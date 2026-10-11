#include <windows.h>

#include <gdiplus.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#pragma comment(lib, "gdiplus.lib")

using TW_INT16 = std::int16_t;
using TW_UINT16 = std::uint16_t;
using TW_UINT32 = std::uint32_t;
using TW_INT32 = std::int32_t;
using TW_MEMREF = void*;

constexpr TW_UINT32 DG_CONTROL = 0x0001;
constexpr TW_UINT32 DG_IMAGE = 0x0002;
constexpr TW_UINT32 DF_DS2 = 0x40000000;

constexpr TW_UINT16 DAT_NULL = 0x0000;
constexpr TW_UINT16 DAT_CAPABILITY = 0x0001;
constexpr TW_UINT16 DAT_EVENT = 0x0002;
constexpr TW_UINT16 DAT_IDENTITY = 0x0003;
constexpr TW_UINT16 DAT_PENDINGXFERS = 0x0005;
constexpr TW_UINT16 DAT_STATUS = 0x0008;
constexpr TW_UINT16 DAT_USERINTERFACE = 0x0009;
constexpr TW_UINT16 DAT_IMAGEINFO = 0x0101;
constexpr TW_UINT16 DAT_IMAGENATIVEXFER = 0x0104;

constexpr TW_UINT16 MSG_GET = 0x0001;
constexpr TW_UINT16 MSG_GETCURRENT = 0x0002;
constexpr TW_UINT16 MSG_RESET = 0x0007;
constexpr TW_UINT16 MSG_OPENDS = 0x0301;
constexpr TW_UINT16 MSG_CLOSEDS = 0x0302;
constexpr TW_UINT16 MSG_ENABLEDS = 0x0501;
constexpr TW_UINT16 MSG_DISABLEDS = 0x0502;
constexpr TW_UINT16 MSG_PROCESSEVENT = 0x0601;
constexpr TW_UINT16 MSG_ENDXFER = 0x0701;

constexpr TW_UINT16 TWRC_SUCCESS = 0;
constexpr TW_UINT16 TWRC_FAILURE = 1;
constexpr TW_UINT16 TWRC_CHECKSTATUS = 2;
constexpr TW_UINT16 TWRC_CANCEL = 3;
constexpr TW_UINT16 TWRC_DSEVENT = 4;
constexpr TW_UINT16 TWRC_NOTDSEVENT = 5;
constexpr TW_UINT16 TWRC_XFERDONE = 6;

constexpr TW_UINT16 TWCC_SUCCESS = 0;
constexpr TW_UINT16 TWCC_CAPUNSUPPORTED = 13;
constexpr TW_UINT16 TWCC_BADPROTOCOL = 9;

constexpr TW_UINT16 MSG_XFERREADY = 0x0101;

constexpr TW_UINT16 ICAP_XFERMECH = 259;
constexpr TW_UINT16 TWTY_UINT16 = 4;
constexpr TW_UINT16 TWSX_NATIVE = 0;
constexpr TW_UINT16 TWON_ONEVALUE = 5;
constexpr TW_INT16 TWPT_GRAY = 1;

constexpr TW_UINT32 GMEM_MOVEABLE = 0x0002;

#pragma pack(push, 2)

struct TW_VERSION {
    TW_UINT16 MajorNum;
    TW_UINT16 MinorNum;
    TW_UINT16 Language;
    TW_UINT16 Country;
    char Info[34];
};

struct TW_IDENTITY {
    TW_UINT32 Id;
    TW_VERSION Version;
    TW_UINT16 ProtocolMajor;
    TW_UINT16 ProtocolMinor;
    TW_UINT32 SupportedGroups;
    char Manufacturer[34];
    char ProductFamily[34];
    char ProductName[34];
};

struct TW_STATUS {
    TW_UINT16 ConditionCode;
    TW_UINT16 Reserved;
};

struct TW_USERINTERFACE {
    TW_UINT16 ShowUI;
    TW_UINT16 ModalUI;
    HWND hParent;
};

struct TW_PENDINGXFERS {
    TW_UINT16 Count;
    TW_UINT32 EOJ;
};

struct TW_EVENT {
    TW_MEMREF pEvent;
    TW_UINT16 TWMessage;
};

struct TW_FIX32 {
    TW_INT16 Whole;
    TW_UINT16 Frac;
};

struct TW_IMAGEINFO {
    TW_FIX32 XResolution;
    TW_FIX32 YResolution;
    TW_INT32 ImageWidth;
    TW_INT32 ImageLength;
    TW_INT16 SamplesPerPixel;
    TW_INT16 BitsPerSample[8];
    TW_INT16 BitsPerPixel;
    TW_UINT16 Planar;
    TW_INT16 PixelType;
    TW_UINT16 Compression;
};

struct TW_CAPABILITY {
    TW_UINT16 Cap;
    TW_UINT16 ConType;
    TW_MEMREF hContainer;
};

struct TW_ONEVALUE {
    TW_UINT16 ItemType;
    TW_UINT32 Item;
};

#pragma pack(pop)

static_assert(sizeof(TW_IDENTITY) == 156, "TW_IDENTITY must match TWAIN/pytwain layout");

namespace {

ULONG_PTR g_gdiplus_token = 0;
TW_STATUS g_status{TWCC_SUCCESS, 0};
bool g_open = false;
bool g_enabled = false;
std::vector<std::wstring> g_pages;
std::size_t g_next_page = 0;
TW_UINT16 g_pending_count = 0;

void ensure_gdiplus() {
    if (g_gdiplus_token != 0) {
        return;
    }
    Gdiplus::GdiplusStartupInput input;
    Gdiplus::GdiplusStartup(&g_gdiplus_token, &input, nullptr);
}

void set_status(TW_UINT16 code) {
    g_status.ConditionCode = code;
}

void copy_text(char* destination, std::size_t size, const char* text) {
    std::memset(destination, 0, size);
    strncpy_s(destination, size, text, _TRUNCATE);
}

void fill_identity(TW_IDENTITY* identity) {
    std::memset(identity, 0, sizeof(TW_IDENTITY));
    identity->Version.MajorNum = 0;
    identity->Version.MinorNum = 1;
    copy_text(identity->Version.Info, sizeof(identity->Version.Info), "Nospe TWAIN PDF Emulator");
    identity->ProtocolMajor = 2;
    identity->ProtocolMinor = 4;
    identity->SupportedGroups = DG_CONTROL | DG_IMAGE | DF_DS2;
    copy_text(identity->Manufacturer, sizeof(identity->Manufacturer), "Nospe");
    copy_text(identity->ProductFamily, sizeof(identity->ProductFamily), "Nospe");
    copy_text(identity->ProductName, sizeof(identity->ProductName), "Nospe Virtual Scanner");
}

std::string default_manifest_path() {
    char* local_app_data = nullptr;
    std::size_t size = 0;
    if (_dupenv_s(&local_app_data, &size, "NOSPE_EMULATOR_MANIFEST") == 0 && local_app_data) {
        std::string configured(local_app_data);
        std::free(local_app_data);
        if (!configured.empty()) {
            return configured;
        }
    }
    if (local_app_data) {
        std::free(local_app_data);
    }

    char* app_data = nullptr;
    size = 0;
    if (_dupenv_s(&app_data, &size, "LOCALAPPDATA") != 0 || !app_data) {
        return {};
    }
    std::string path(app_data);
    std::free(app_data);
    return path + "\\Nospe\\twain-emulator\\active\\manifest.json";
}

std::string read_file(const std::string& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        return {};
    }
    std::ostringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

std::wstring utf8_to_wide(const std::string& value) {
    if (value.empty()) {
        return {};
    }
    const int length = MultiByteToWideChar(CP_UTF8, 0, value.c_str(), -1, nullptr, 0);
    if (length <= 0) {
        return {};
    }
    std::wstring wide(static_cast<std::size_t>(length), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, value.c_str(), -1, wide.data(), length);
    if (!wide.empty() && wide.back() == L'\0') {
        wide.pop_back();
    }
    return wide;
}

std::vector<std::wstring> extract_page_paths(const std::string& manifest) {
    std::vector<std::wstring> paths;
    const std::string key = "\"path\"";
    std::size_t cursor = 0;
    while ((cursor = manifest.find(key, cursor)) != std::string::npos) {
        const std::size_t colon = manifest.find(':', cursor + key.size());
        const std::size_t first_quote = manifest.find('"', colon == std::string::npos ? cursor : colon);
        const std::size_t second_quote = manifest.find('"', first_quote + 1);
        if (first_quote == std::string::npos || second_quote == std::string::npos) {
            break;
        }
        const std::string raw = manifest.substr(first_quote + 1, second_quote - first_quote - 1);
        const std::wstring wide = utf8_to_wide(raw);
        if (!wide.empty()) {
            paths.push_back(wide);
        }
        cursor = second_quote + 1;
    }
    return paths;
}

bool load_manifest() {
    g_pages = extract_page_paths(read_file(default_manifest_path()));
    g_next_page = 0;
    g_pending_count = static_cast<TW_UINT16>(g_pages.size());
    return !g_pages.empty();
}

TW_FIX32 make_fix32(double value) {
    const std::int32_t fixed = static_cast<std::int32_t>(value * 65536.0 + 0.5);
    TW_FIX32 result{};
    result.Whole = static_cast<TW_INT16>(fixed >> 16);
    result.Frac = static_cast<TW_UINT16>(fixed & 0xFFFF);
    return result;
}

bool query_image_size(const std::wstring& path, TW_INT32* width, TW_INT32* height) {
    ensure_gdiplus();
    Gdiplus::Bitmap bitmap(path.c_str());
    if (bitmap.GetLastStatus() != Gdiplus::Ok) {
        return false;
    }
    *width = static_cast<TW_INT32>(bitmap.GetWidth());
    *height = static_cast<TW_INT32>(bitmap.GetHeight());
    return *width > 0 && *height > 0;
}

HGLOBAL create_dib_from_png(const std::wstring& path) {
    ensure_gdiplus();
    Gdiplus::Bitmap bitmap(path.c_str());
    if (bitmap.GetLastStatus() != Gdiplus::Ok) {
        return nullptr;
    }

    const INT width = static_cast<INT>(bitmap.GetWidth());
    const INT height = static_cast<INT>(bitmap.GetHeight());
    if (width <= 0 || height <= 0) {
        return nullptr;
    }

    BITMAPINFO bmi{};
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = width;
    bmi.bmiHeader.biHeight = -height;
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 24;
    bmi.bmiHeader.biCompression = BI_RGB;

    void* bits = nullptr;
    HDC hdc = CreateCompatibleDC(nullptr);
    if (!hdc) {
        return nullptr;
    }

    HBITMAP dib = CreateDIBSection(hdc, &bmi, DIB_RGB_COLORS, &bits, nullptr, 0);
    if (!dib || !bits) {
        DeleteDC(hdc);
        return nullptr;
    }

    HBITMAP old = static_cast<HBITMAP>(SelectObject(hdc, dib));
    Gdiplus::Graphics graphics(hdc);
    graphics.SetInterpolationMode(Gdiplus::InterpolationModeHighQualityBicubic);
    graphics.DrawImage(&bitmap, 0, 0, width, height);
    SelectObject(hdc, old);
    DeleteDC(hdc);

    const DWORD header_size = sizeof(BITMAPINFOHEADER);
    const DWORD pixel_size = static_cast<DWORD>(
        ((width * 24 + 31) / 32) * 4 * static_cast<DWORD>(height));
    const DWORD total = header_size + pixel_size;

    HGLOBAL handle = GlobalAlloc(GMEM_MOVEABLE, total);
    if (!handle) {
        DeleteObject(dib);
        return nullptr;
    }

    void* locked = GlobalLock(handle);
    if (!locked) {
        GlobalFree(handle);
        DeleteObject(dib);
        return nullptr;
    }

    auto* destination = static_cast<std::uint8_t*>(locked);
    std::memcpy(destination, &bmi.bmiHeader, header_size);
    GetDIBits(
        CreateCompatibleDC(nullptr),
        dib,
        0,
        static_cast<UINT>(height),
        destination + header_size,
        &bmi,
        DIB_RGB_COLORS);
    GlobalUnlock(handle);
    DeleteObject(dib);
    return handle;
}

TW_UINT16 handle_capability(TW_UINT16 msg, TW_MEMREF data) {
    if (!data || msg != MSG_GETCURRENT) {
        set_status(TWCC_CAPUNSUPPORTED);
        return TWRC_FAILURE;
    }

    auto* capability = static_cast<TW_CAPABILITY*>(data);
    if (capability->Cap != ICAP_XFERMECH) {
        set_status(TWCC_CAPUNSUPPORTED);
        return TWRC_FAILURE;
    }

    HGLOBAL container = GlobalAlloc(GMEM_MOVEABLE, sizeof(TW_ONEVALUE));
    if (!container) {
        set_status(TWCC_BADPROTOCOL);
        return TWRC_FAILURE;
    }

    auto* value = static_cast<TW_ONEVALUE*>(GlobalLock(container));
    value->ItemType = TWTY_UINT16;
    value->Item = TWSX_NATIVE;
    GlobalUnlock(container);

    capability->ConType = TWON_ONEVALUE;
    capability->hContainer = container;
    set_status(TWCC_SUCCESS);
    return TWRC_SUCCESS;
}

TW_UINT16 handle_pending_xfers(TW_UINT16 msg, TW_MEMREF data) {
    auto* pending = static_cast<TW_PENDINGXFERS*>(data);
    if (!pending) {
        set_status(TWCC_BADPROTOCOL);
        return TWRC_FAILURE;
    }

    if (msg == MSG_GET || msg == MSG_GETCURRENT) {
        pending->Count = g_pending_count;
        pending->EOJ = 0;
        set_status(TWCC_SUCCESS);
        return TWRC_SUCCESS;
    }

    if (msg == MSG_ENDXFER) {
        if (g_pending_count > 0) {
            --g_pending_count;
        }
        ++g_next_page;
        pending->Count = g_pending_count;
        pending->EOJ = 0;
        set_status(TWCC_SUCCESS);
        return TWRC_SUCCESS;
    }

    if (msg == MSG_RESET) {
        g_pending_count = 0;
        g_next_page = g_pages.size();
        pending->Count = 0;
        pending->EOJ = 0;
        set_status(TWCC_SUCCESS);
        return TWRC_SUCCESS;
    }

    set_status(TWCC_BADPROTOCOL);
    return TWRC_FAILURE;
}

TW_UINT16 handle_control(TW_UINT16 dat, TW_UINT16 msg, TW_MEMREF data) {
    switch (dat) {
        case DAT_IDENTITY:
            if (msg == MSG_GET && data) {
                fill_identity(static_cast<TW_IDENTITY*>(data));
                set_status(TWCC_SUCCESS);
                return TWRC_SUCCESS;
            }
            break;
        case DAT_STATUS:
            if (msg == MSG_GET && data) {
                *static_cast<TW_STATUS*>(data) = g_status;
                return TWRC_SUCCESS;
            }
            break;
        case DAT_NULL:
            if (msg == MSG_OPENDS) {
                g_open = true;
                set_status(TWCC_SUCCESS);
                return TWRC_SUCCESS;
            }
            if (msg == MSG_CLOSEDS) {
                g_open = false;
                g_enabled = false;
                g_pages.clear();
                g_next_page = 0;
                g_pending_count = 0;
                set_status(TWCC_SUCCESS);
                return TWRC_SUCCESS;
            }
            break;
        case DAT_USERINTERFACE:
            if (msg == MSG_ENABLEDS) {
                if (!g_open || !load_manifest()) {
                    set_status(TWCC_SUCCESS);
                    return TWRC_FAILURE;
                }
                g_enabled = true;
                set_status(TWCC_SUCCESS);
                return TWRC_SUCCESS;
            }
            if (msg == MSG_DISABLEDS) {
                g_enabled = false;
                set_status(TWCC_SUCCESS);
                return TWRC_SUCCESS;
            }
            break;
        case DAT_EVENT:
            if (msg == MSG_PROCESSEVENT && data) {
                auto* event = static_cast<TW_EVENT*>(data);
                if (!g_enabled || g_pending_count == 0 || g_next_page >= g_pages.size()) {
                    event->TWMessage = 0;
                    return TWRC_NOTDSEVENT;
                }
                event->TWMessage = MSG_XFERREADY;
                set_status(TWCC_SUCCESS);
                return TWRC_DSEVENT;
            }
            break;
        case DAT_PENDINGXFERS:
            return handle_pending_xfers(msg, data);
        case DAT_CAPABILITY:
            return handle_capability(msg, data);
        default:
            break;
    }

    set_status(TWCC_BADPROTOCOL);
    return TWRC_FAILURE;
}

TW_UINT16 handle_image(TW_UINT16 dat, TW_UINT16 msg, TW_MEMREF data) {
    if (!g_enabled || g_next_page >= g_pages.size()) {
        set_status(TWCC_BADPROTOCOL);
        return TWRC_FAILURE;
    }

    const std::wstring& current = g_pages[g_next_page];

    if (dat == DAT_IMAGEINFO && msg == MSG_GET && data) {
        TW_INT32 width = 0;
        TW_INT32 height = 0;
        if (!query_image_size(current, &width, &height)) {
            set_status(TWCC_BADPROTOCOL);
            return TWRC_FAILURE;
        }

        auto* info = static_cast<TW_IMAGEINFO*>(data);
        std::memset(info, 0, sizeof(TW_IMAGEINFO));
        info->XResolution = make_fix32(300.0);
        info->YResolution = make_fix32(300.0);
        info->ImageWidth = width;
        info->ImageLength = height;
        info->SamplesPerPixel = 1;
        info->BitsPerSample[0] = 8;
        info->BitsPerPixel = 24;
        info->Planar = 0;
        info->PixelType = TWPT_GRAY;
        info->Compression = 0;
        set_status(TWCC_SUCCESS);
        return TWRC_SUCCESS;
    }

    if (dat == DAT_IMAGENATIVEXFER && msg == MSG_GET && data) {
        HGLOBAL dib = create_dib_from_png(current);
        if (!dib) {
            set_status(TWCC_BADPROTOCOL);
            return TWRC_FAILURE;
        }
        *static_cast<HGLOBAL*>(data) = dib;
        set_status(TWCC_SUCCESS);
        return TWRC_XFERDONE;
    }

    set_status(TWCC_BADPROTOCOL);
    return TWRC_FAILURE;
}

}  // namespace

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
        ensure_gdiplus();
    } else if (reason == DLL_PROCESS_DETACH && g_gdiplus_token != 0) {
        Gdiplus::GdiplusShutdown(g_gdiplus_token);
        g_gdiplus_token = 0;
    }
    return TRUE;
}

extern "C" __declspec(dllexport) TW_UINT16 __stdcall DS_Entry(
    TW_IDENTITY* /*origin*/,
    TW_UINT32 data_group,
    TW_UINT16 data_argument_type,
    TW_UINT16 message,
    TW_MEMREF data) {
    if (data_group == DG_CONTROL) {
        return handle_control(data_argument_type, message, data);
    }
    if (data_group == DG_IMAGE) {
        return handle_image(data_argument_type, message, data);
    }

    set_status(TWCC_BADPROTOCOL);
    return TWRC_FAILURE;
}
