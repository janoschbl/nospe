// Nospe Tauri 2 Entry-Point.
//
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

use std::fs::OpenOptions;
use std::io::{ErrorKind, Read, Write};
use std::net::TcpStream;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::Manager;

struct BackendProcess(Mutex<Option<Child>>);
struct BackendStartLock(Mutex<Option<std::path::PathBuf>>);

fn backend_is_healthy() -> bool {
    let Ok(mut stream) = TcpStream::connect("127.0.0.1:8765") else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(300)));
    if stream
        .write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        .is_err()
    {
        return false;
    }
    let mut response = String::new();
    stream.read_to_string(&mut response).is_ok()
        && response.starts_with("HTTP/1.1 200")
        && response.contains("\"ok\":true")
}

fn wait_for_backend() -> bool {
    (0..50).any(|_| {
        if backend_is_healthy() {
            true
        } else {
            thread::sleep(Duration::from_millis(100));
            false
        }
    })
}

fn acquire_backend_start_lock() -> Result<Option<std::path::PathBuf>, String> {
    let lock_path = std::env::temp_dir().join("nospe-backend-start.lock");
    let open_lock = || OpenOptions::new().write(true).create_new(true).open(&lock_path);
    match open_lock() {
        Ok(_) => Ok(Some(lock_path)),
        Err(error) if error.kind() == ErrorKind::AlreadyExists => {
            // A forced shutdown can leave this file behind. Only replace a
            // clearly stale lock, so concurrent normal starts still wait for
            // the first sidecar instead of racing for the API port.
            let is_stale = std::fs::metadata(&lock_path)
                .ok()
                .and_then(|metadata| metadata.modified().ok())
                .and_then(|modified| modified.elapsed().ok())
                .is_some_and(|age| age > Duration::from_secs(15));
            if !is_stale {
                return Ok(None);
            }
            let _ = std::fs::remove_file(&lock_path);
            open_lock()
                .map(|_| Some(lock_path))
                .map_err(|error| format!("backend start lock unavailable: {error}"))
        }
        Err(error) => Err(format!("backend start lock unavailable: {error}")),
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess(Mutex::new(None)))
        .manage(BackendStartLock(Mutex::new(None)))
        .setup(|app| {
            let backend_path = app
                .path()
                .resource_dir()
                .expect("resource directory unavailable")
                .join("nospe-backend.exe");
            // Reuse an already healthy sidecar. This prevents duplicate app
            // launches from racing for the fixed local API port.
            if !backend_is_healthy() && backend_path.exists() {
                if let Some(lock_path) = acquire_backend_start_lock()
                    .map_err(|error| -> Box<dyn std::error::Error> { error.into() })?
                {
                    let child = Command::new(&backend_path)
                        .spawn()
                        .map_err(|error| format!("bundled Nospe backend could not be started: {error}"))?;
                    app.state::<BackendProcess>()
                        .0
                        .lock()
                        .expect("backend state poisoned")
                        .replace(child);
                    app.state::<BackendStartLock>()
                        .0
                        .lock()
                        .expect("backend lock state poisoned")
                        .replace(lock_path);
                }
            }
            if !wait_for_backend() {
                return Err("Nospe backend did not become healthy on 127.0.0.1:8765".into());
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Nospe")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(child) = app
                    .state::<BackendProcess>()
                    .0
                    .lock()
                    .expect("backend state poisoned")
                    .as_mut()
                {
                    let _ = child.kill();
                }
                if let Some(lock_path) = app
                    .state::<BackendStartLock>()
                    .0
                    .lock()
                    .expect("backend lock state poisoned")
                    .take()
                {
                    let _ = std::fs::remove_file(lock_path);
                }
            }
        });
}
