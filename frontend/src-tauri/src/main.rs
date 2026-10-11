// Nospe Tauri 2 Entry-Point.
//
// Das Python-Backend wird als Sidecar gestartet. Die UI erfährt Port und
// Secret ausschließlich über das Tauri-Kommando `backend_config`; beides wird
// bei jedem Start neu erzeugt (siehe backend/run_backend.py).
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use serde::Serialize;
use tauri::Manager;

// Der erste Start entpackt den PyInstaller-Sidecar und wird vom Virenscanner
// geprüft; das kann deutlich länger als ein paar Sekunden dauern.
const BACKEND_START_TIMEOUT: Duration = Duration::from_secs(60);

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackendConfig {
    base_url: String,
    secret: String,
}

struct BackendState {
    config: Mutex<Option<BackendConfig>>,
    child: Mutex<Option<Child>>,
}

#[tauri::command]
fn backend_config(state: tauri::State<BackendState>) -> Result<BackendConfig, String> {
    state
        .config
        .lock()
        .map_err(|_| "backend state poisoned".to_string())?
        .clone()
        .ok_or_else(|| "backend not ready".to_string())
}

/// Fragt `/health` mit dem Secret ab. Ein fremder Prozess auf dem Port kennt
/// das Secret nicht und besteht die Prüfung daher nicht.
fn backend_is_healthy(port: u16, secret: &str) -> bool {
    let Ok(mut stream) = TcpStream::connect(("127.0.0.1", port)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
    let request = format!(
        "GET /health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nX-Nospe-Token: {secret}\r\nConnection: close\r\n\r\n"
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return false;
    }
    let mut response = String::new();
    stream.read_to_string(&mut response).is_ok()
        && response.starts_with("HTTP/1.1 200")
        && response.contains("\"ok\":true")
}

fn wait_until<T>(timeout: Duration, mut probe: impl FnMut() -> Option<T>) -> Option<T> {
    let deadline = Instant::now() + timeout;
    loop {
        if let Some(value) = probe() {
            return Some(value);
        }
        if Instant::now() >= deadline {
            return None;
        }
        thread::sleep(Duration::from_millis(100));
    }
}

/// Liest die Handshake-Datei des Backends: Zeile 1 = Port, Zeile 2 = Secret.
fn read_handshake(path: &PathBuf) -> Option<(u16, String)> {
    let content = std::fs::read_to_string(path).ok()?;
    let mut lines = content.lines();
    let port = lines.next()?.trim().parse::<u16>().ok()?;
    let secret = lines.next()?.trim().to_string();
    if secret.len() < 16 {
        return None;
    }
    Some((port, secret))
}

fn handshake_path() -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    std::env::temp_dir().join(format!("nospe-handshake-{}-{nanos}.txt", std::process::id()))
}

/// Entwicklung: ein manuell gestartetes Backend (`NOSPE_API_PORT` und
/// `NOSPE_API_SECRET` gesetzt) wird genutzt, statt den Sidecar zu starten.
fn external_backend() -> Option<(u16, String)> {
    let port = std::env::var("NOSPE_API_PORT").ok()?.trim().parse::<u16>().ok()?;
    let secret = std::env::var("NOSPE_API_SECRET").ok()?.trim().to_string();
    if secret.is_empty() {
        return None;
    }
    Some((port, secret))
}

fn start_sidecar(app: &tauri::App) -> Result<(Child, u16, String), String> {
    let backend_path = app
        .path()
        .resource_dir()
        .map_err(|error| format!("resource directory unavailable: {error}"))?
        .join("nospe-backend.exe");
    if !backend_path.exists() {
        return Err(format!(
            "Nospe backend not found at {}. For development start the backend manually and set NOSPE_API_PORT and NOSPE_API_SECRET.",
            backend_path.display()
        ));
    }
    let handshake = handshake_path();
    let mut child = Command::new(&backend_path)
        .env("NOSPE_HANDSHAKE_FILE", &handshake)
        // Das Backend beendet sich selbst, wenn dieser Prozess verschwindet
        // (PyInstaller-onefile startet einen Kindprozess, den `kill()` nicht trifft).
        .env("NOSPE_PARENT_PID", std::process::id().to_string())
        .spawn()
        .map_err(|error| format!("bundled Nospe backend could not be started: {error}"))?;

    let published = wait_until(BACKEND_START_TIMEOUT, || {
        if let Ok(Some(status)) = child.try_wait() {
            // Sidecar ist schon wieder beendet: nicht weiter warten.
            eprintln!("Nospe backend exited early: {status}");
            return Some(None);
        }
        read_handshake(&handshake).map(Some)
    })
    .flatten();
    let _ = std::fs::remove_file(&handshake);

    match published {
        Some((port, secret)) => Ok((child, port, secret)),
        None => {
            let _ = child.kill();
            Err("Nospe backend did not publish its port in time".to_string())
        }
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendState {
            config: Mutex::new(None),
            child: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![backend_config])
        .setup(|app| {
            let (port, secret) = match external_backend() {
                Some(found) => found,
                None => {
                    let (child, port, secret) = start_sidecar(app)?;
                    *app.state::<BackendState>()
                        .child
                        .lock()
                        .expect("backend child state poisoned") = Some(child);
                    (port, secret)
                }
            };

            let healthy = wait_until(BACKEND_START_TIMEOUT, || {
                backend_is_healthy(port, &secret).then_some(())
            });
            if healthy.is_none() {
                return Err(format!("Nospe backend did not become healthy on 127.0.0.1:{port}").into());
            }

            *app.state::<BackendState>()
                .config
                .lock()
                .expect("backend config state poisoned") = Some(BackendConfig {
                base_url: format!("http://127.0.0.1:{port}"),
                secret,
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Nospe")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(child) = app
                    .state::<BackendState>()
                    .child
                    .lock()
                    .expect("backend child state poisoned")
                    .as_mut()
                {
                    let _ = child.kill();
                }
            }
        });
}
