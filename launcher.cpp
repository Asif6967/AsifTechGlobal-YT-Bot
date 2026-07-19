/*
 ██████╗ ███████╗██╗███████╗████████╗███████╗ ██████╗██╗  ██╗
 ██╔══██╗██╔════╝██║██╔════╝╚══██╔══╝██╔════╝██╔════╝██║  ██║
 ██████╔╝███████╗██║█████╗     ██║   █████╗  ██║     ███████║
 ██╔══██╗╚════██║██║██╔══╝     ██║   ██╔══╝  ██║     ██╔══██║
 ██████╔╝███████║██║██║        ██║   ███████╗╚██████╗██║  ██║
 ╚═════╝ ╚══════╝╚═╝╚═╝        ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝

 AsifTechGlobal — YT Bot Launcher  v1.0
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 • Voice greeting via Windows Speech Synthesis
 • Personalized name-based welcome
 • YouTube-style dark dashboard with clickable cards
 • Launches bot, web panel, logs, URLs, messages, settings

 Build (MinGW / WinLibs — see build.bat):
   g++ -std=c++17 -O2 -o launcher.exe launcher.cpp ^
       -lgdiplus -ldwmapi -lshell32 -lcomctl32 -mwindows

 Build (MSVC):
   cl /EHsc /O2 launcher.cpp /link gdiplus.lib dwmapi.lib shell32.lib comctl32.lib
*/

#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN

#include <windows.h>
#include <windowsx.h>
#include <gdiplus.h>
#include <dwmapi.h>
#include <shellapi.h>
#include <commctrl.h>
#include <string>
#include <vector>
#include <cctype>

#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "comctl32.lib")
#pragma comment(linker, "/SUBSYSTEM:WINDOWS")

using namespace Gdiplus;

// ════════════════════════════════════════════════════════════════════════════
//  THEME  — matches the web panel dark design
// ════════════════════════════════════════════════════════════════════════════

const Color C_BG   (255,  13,  17,  23);   // #0d1117
const Color C_BG2  (255,  22,  27,  34);   // #161b22
const Color C_BG3  (255,  33,  38,  45);   // #21262d
const Color C_TEXT (255, 230, 237, 243);   // #e6edf3
const Color C_MUTED(255, 139, 148, 158);   // #8b949e
const Color C_GREEN(255,   0, 255, 136);   // #00ff88
const Color C_GBTN (255,  35, 134,  54);   // #238636
const Color C_BLUE (255,  31, 111, 235);   // #1f6feb
const Color C_YTR1 (255, 205,   0,   0);   // YouTube red (bright)
const Color C_YTR2 (255, 145,   0,   0);   // YouTube red (dark)

// Card gradient pairs  [top, bottom]
struct CardTheme { Color c1, c2; };
const CardTheme THEMES[6] = {
    { Color(255, 40,150, 60), Color(255, 20, 80, 35) },   // green  – Bot
    { Color(255, 31,111,235), Color(255, 15, 65,160) },   // blue   – Web Panel
    { Color(255,130, 80,220), Color(255, 75, 35,155) },   // purple – Logs
    { Color(255,210,120, 30), Color(255,140, 65, 10) },   // orange – URLs
    { Color(255, 20,150,150), Color(255, 10, 90, 90) },   // teal   – Messages
    { Color(255, 75, 80, 95), Color(255, 40, 42, 52) },   // gray   – Settings
};

// ════════════════════════════════════════════════════════════════════════════
//  GLOBALS
// ════════════════════════════════════════════════════════════════════════════

ULONG_PTR     g_gdip     = 0;
HINSTANCE     g_hInst    = nullptr;
HWND          g_loginWnd = nullptr;
HWND          g_mainWnd  = nullptr;
HWND          g_hEdit    = nullptr;
std::wstring  g_userName = L"Friend";
wchar_t       g_dir[MAX_PATH] = {};

// Card data
struct Card {
    float x, y, w, h;
    const wchar_t* label;   // short icon text
    const wchar_t* title;
    const wchar_t* desc;
    CardTheme      theme;
    int            action;
    bool           hovered = false;
};
std::vector<Card> g_cards;

// Control IDs
#define ID_EDIT_NAME  101
#define ACT_BOT       0
#define ACT_PANEL     1
#define ACT_LOGS      2
#define ACT_URLS      3
#define ACT_MSGS      4
#define ACT_CFG       5

// ════════════════════════════════════════════════════════════════════════════
//  TEXT-TO-SPEECH  (PowerShell .NET — no extra headers needed)
// ════════════════════════════════════════════════════════════════════════════

void SpeakAsync(const std::wstring& raw) {
    // Sanitize: remove single-quotes and backslashes for safe PS injection
    std::wstring t;
    t.reserve(raw.size());
    for (wchar_t c : raw)
        if (c != L'\'' && c != L'\\' && c != L'"') t += c;

    std::wstring ps =
        L"Add-Type -AssemblyName System.Speech;"
        L"$v=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        L"$v.Rate=-2;$v.Volume=100;"
        L"$v.Speak('" + t + L"');";

    std::wstring cmd =
        L"powershell.exe -WindowStyle Hidden -NonInteractive -Command \"" + ps + L"\"";

    STARTUPINFOW si  = { sizeof(si) };
    si.dwFlags       = STARTF_USESHOWWINDOW;
    si.wShowWindow   = SW_HIDE;
    PROCESS_INFORMATION pi = {};
    CreateProcessW(nullptr, cmd.data(), nullptr, nullptr,
                   FALSE, CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi);
    if (pi.hProcess) CloseHandle(pi.hProcess);
    if (pi.hThread)  CloseHandle(pi.hThread);
}

// ════════════════════════════════════════════════════════════════════════════
//  DARK TITLE BAR  (Windows 10 20H1+ / Windows 11)
// ════════════════════════════════════════════════════════════════════════════

void DarkTitle(HWND hwnd) {
    BOOL d = TRUE;
    DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, &d, sizeof(d));
    COLORREF bg = RGB(13, 17, 23);
    DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, &bg, sizeof(bg));
    COLORREF txt = RGB(230, 237, 243);
    DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, &txt, sizeof(txt));
}

// ════════════════════════════════════════════════════════════════════════════
//  GDI+ HELPERS
// ════════════════════════════════════════════════════════════════════════════

static void FillRRect(Graphics& g, const Brush* b,
                       float x, float y, float w, float h, float r = 10.f) {
    GraphicsPath p;
    p.AddArc(x,       y,       r*2, r*2, 180, 90);
    p.AddArc(x+w-r*2, y,       r*2, r*2, 270, 90);
    p.AddArc(x+w-r*2, y+h-r*2, r*2, r*2,   0, 90);
    p.AddArc(x,       y+h-r*2, r*2, r*2,  90, 90);
    p.CloseFigure();
    g.FillPath(b, &p);
}

static void BorderRRect(Graphics& g, const Pen* p,
                         float x, float y, float w, float h, float r = 10.f) {
    GraphicsPath path;
    path.AddArc(x,       y,       r*2, r*2, 180, 90);
    path.AddArc(x+w-r*2, y,       r*2, r*2, 270, 90);
    path.AddArc(x+w-r*2, y+h-r*2, r*2, r*2,   0, 90);
    path.AddArc(x,       y+h-r*2, r*2, r*2,  90, 90);
    path.CloseFigure();
    g.DrawPath(p, &path);
}

static void Txt(Graphics& g, const wchar_t* s, Font* f, const Brush* b,
                float x, float y, float w, float h,
                StringAlignment ha = StringAlignmentNear,
                StringAlignment va = StringAlignmentNear,
                bool wrap = false) {
    RectF r(x, y, w, h);
    StringFormat fmt;
    fmt.SetAlignment(ha);
    fmt.SetLineAlignment(va);
    if (!wrap) {
        fmt.SetFormatFlags(StringFormatFlagsNoWrap);
        fmt.SetTrimming(StringTrimmingEllipsisCharacter);
    }
    g.DrawString(s, -1, f, r, &fmt, b);
}

// ════════════════════════════════════════════════════════════════════════════
//  LAUNCH ACTIONS
// ════════════════════════════════════════════════════════════════════════════

void ShellOpen(const wchar_t* url) {
    ShellExecuteW(nullptr, L"open", url, nullptr, nullptr, SW_SHOWNORMAL);
}

void RunPy(const wchar_t* script) {
    std::wstring cmd = std::wstring(L"python \"") + g_dir + L"\\" + script + L"\"";
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = {};
    CreateProcessW(nullptr, cmd.data(), nullptr, nullptr,
                   FALSE, 0, nullptr, g_dir, &si, &pi);
    if (pi.hProcess) CloseHandle(pi.hProcess);
    if (pi.hThread)  CloseHandle(pi.hThread);
}

void OpenFile(const wchar_t* name) {
    std::wstring p = std::wstring(g_dir) + L"\\" + name;
    ShellExecuteW(nullptr, L"open", p.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
}

void DoAction(int a) {
    switch (a) {
    case ACT_BOT:   RunPy(L"bot.py");
                    SpeakAsync(L"Bot is starting. Good luck " + g_userName);       break;
    case ACT_PANEL: RunPy(L"web_panel.py");
                    Sleep(1200);
                    ShellOpen(L"http://localhost:5000");
                    SpeakAsync(L"Opening web panel for " + g_userName);            break;
    case ACT_LOGS:  OpenFile(L"send_log.txt");                                     break;
    case ACT_URLS:  OpenFile(L"urls.txt");                                         break;
    case ACT_MSGS:  OpenFile(L"messages.txt");                                     break;
    case ACT_CFG:   OpenFile(L"config.json");                                      break;
    }
}

// ════════════════════════════════════════════════════════════════════════════
//  LOGIN  WINDOW
// ════════════════════════════════════════════════════════════════════════════

static void RepositionEdit(HWND hwnd) {
    if (!g_hEdit) return;
    RECT rc; GetClientRect(hwnd, &rc);
    int W = rc.right, H = rc.bottom;
    int cw = 380, ch = 480;
    int cx = (W - cw) / 2, cy = (H - ch) / 2;
    MoveWindow(g_hEdit, cx + 44, cy + 226, cw - 88, 30, TRUE);
}

static void PaintLogin(HWND hwnd) {
    PAINTSTRUCT ps;
    HDC hdc = BeginPaint(hwnd, &ps);
    RECT rc; GetClientRect(hwnd, &rc);
    int W = rc.right, H = rc.bottom;

    HDC mdc = CreateCompatibleDC(hdc);
    HBITMAP bmp = CreateCompatibleBitmap(hdc, W, H);
    HBITMAP old = (HBITMAP)SelectObject(mdc, bmp);

    Graphics g(mdc);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    g.SetTextRenderingHint(TextRenderingHintClearTypeGridFit);

    // Background with subtle gradient glow
    SolidBrush bgBr(C_BG);
    g.FillRectangle(&bgBr, 0, 0, W, H);
    LinearGradientBrush glowBr(PointF((float)W*0.5f, 0),
                                PointF((float)W*0.5f, (float)H),
                                Color(18, 0, 255, 136),
                                Color(0,  0, 255, 136));
    g.FillRectangle(&glowBr, 0, 0, W, H);

    // ── Card ──
    int cw = 380, ch = 480;
    int cx = (W - cw) / 2, cy = (H - ch) / 2;

    SolidBrush cardBr(C_BG2);
    FillRRect(g, &cardBr, (float)cx, (float)cy, (float)cw, (float)ch, 14.f);
    Pen borderPen(C_BG3, 1.f);
    BorderRRect(g, &borderPen, (float)cx, (float)cy, (float)cw, (float)ch, 14.f);

    // ── Logo ──
    float lx = cx + cw / 2.f, ly = cy + 68.f;

    // Glow rings
    for (int r = 48; r > 32; r -= 4) {
        BYTE alpha = (BYTE)((48 - r) * 8);
        Color gc(alpha, 0, 255, 136);
        SolidBrush gb(gc);
        g.FillEllipse(&gb, lx - r, ly - r, (float)(r * 2), (float)(r * 2));
    }
    // Circle
    SolidBrush greenBr(C_GREEN);
    g.FillEllipse(&greenBr, lx - 32.f, ly - 32.f, 64.f, 64.f);
    // ▶ Triangle
    PointF tri[3] = { {lx - 11.f, ly - 15.f}, {lx + 16.f, ly}, {lx - 11.f, ly + 15.f} };
    SolidBrush dbr(C_BG);
    g.FillPolygon(&dbr, tri, 3);

    // ── App name ──
    Font fTitle(L"Segoe UI", 23, FontStyleBold, UnitPixel);
    Font fSub  (L"Segoe UI", 11, FontStyleRegular, UnitPixel);
    Font fLabel(L"Segoe UI", 12, FontStyleRegular, UnitPixel);
    Font fBtn  (L"Segoe UI", 14, FontStyleBold, UnitPixel);
    Font fFoot (L"Segoe UI", 10, FontStyleRegular, UnitPixel);

    SolidBrush wBr(C_TEXT), mBr(C_MUTED), gBr(C_GREEN);

    Txt(g, L"AsifTechGlobal", &fTitle, &wBr,
        (float)cx, (float)(cy + 112), (float)cw, 32,
        StringAlignmentCenter);
    Txt(g, L"YouTube Live Bot Dashboard", &fSub, &mBr,
        (float)cx, (float)(cy + 148), (float)cw, 22,
        StringAlignmentCenter);

    // Divider 1
    Pen divPen(C_BG3, 1.f);
    g.DrawLine(&divPen, (float)(cx+22), (float)(cy+180),
               (float)(cx+cw-22), (float)(cy+180));

    // Label
    Txt(g, L"Enter your name to continue:", &fLabel, &mBr,
        (float)(cx + 30), (float)(cy + 194), (float)(cw - 60), 22);

    // Edit box background (real EDIT control sits on top)
    SolidBrush ebBg(C_BG);
    Pen ebBorder(Color(255, 48, 54, 61), 1.5f);
    FillRRect(g, &ebBg, (float)(cx+30), (float)(cy+220), (float)(cw-60), 40, 7.f);
    BorderRRect(g, &ebBorder, (float)(cx+30), (float)(cy+220), (float)(cw-60), 40, 7.f);

    // ── Get Started button ──
    LinearGradientBrush btnGr(
        PointF(0.f, (float)(cy + 274)),
        PointF(0.f, (float)(cy + 322)),
        Color(255, 48, 160, 72),
        Color(255, 25, 108, 38));
    FillRRect(g, &btnGr, (float)(cx+30), (float)(cy+274), (float)(cw-60), 48, 9.f);
    Txt(g, L"Get Started  \u2192", &fBtn, &wBr,
        (float)(cx+30), (float)(cy+274), (float)(cw-60), 48,
        StringAlignmentCenter, StringAlignmentCenter);

    // Divider 2
    g.DrawLine(&divPen, (float)(cx+22), (float)(cy+338),
               (float)(cx+cw-22), (float)(cy+338));

    // Footer
    SolidBrush dimBr(Color(255, 72, 82, 95));
    Txt(g, L"\u26a1 AsifTechGlobal Bot System  |  v1.0",
        &fFoot, &dimBr, (float)cx, (float)(cy + 350), (float)cw, 18, StringAlignmentCenter);
    Txt(g, L"PC + Mobile supported via same Wi-Fi",
        &fFoot, &dimBr, (float)cx, (float)(cy + 372), (float)cw, 18, StringAlignmentCenter);
    Txt(g, L"Login to access your personal bot dashboard",
        &fFoot, &dimBr, (float)cx, (float)(cy + 394), (float)cw, 18, StringAlignmentCenter);

    BitBlt(hdc, 0, 0, W, H, mdc, 0, 0, SRCCOPY);
    SelectObject(mdc, old);
    DeleteObject(bmp);
    DeleteDC(mdc);
    EndPaint(hwnd, &ps);
}

static void OnLoginSubmit(HWND hwnd) {
    wchar_t buf[128] = {};
    GetWindowTextW(g_hEdit, buf, 127);
    std::wstring name = buf;
    while (!name.empty() && name.front() == L' ') name.erase(name.begin());
    while (!name.empty() && name.back()  == L' ') name.pop_back();
    if (name.empty()) { name = L"Friend"; }
    g_userName = name;

    // Build cards with correct size before showing main window
    RECT mr; GetClientRect(g_mainWnd, &mr);
    // If not yet shown, use default
    if (mr.right == 0) { mr.right = 1120; mr.bottom = 700; }

    // Rebuild cards for actual client area
    RECT rcM; GetWindowRect(g_mainWnd, &rcM);
    int mw = rcM.right - rcM.left, mh = rcM.bottom - rcM.top;

    // Update window title with user name
    SetWindowTextW(g_mainWnd,
        (std::wstring(L"AsifTechGlobal \u2014 Welcome, ") + g_userName + L"!").c_str());

    ShowWindow(g_mainWnd, SW_SHOWMAXIMIZED);
    UpdateWindow(g_mainWnd);

    DestroyWindow(hwnd);   // closes login, keeps app alive via mainWnd

    // Speak greeting asynchronously
    SpeakAsync(L"Welcome " + g_userName +
               L"! Your AsifTechGlobal YouTube Bot dashboard is ready. "
               L"Click any card to launch a feature.");
}

LRESULT CALLBACK LoginWndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_CREATE:
        // Initial greeting
        SpeakAsync(L"Welcome to AsifTech Global. Please enter your name to continue.");
        // Create edit control (repositioned in WM_SIZE)
        g_hEdit = CreateWindowExW(0, L"EDIT", L"",
            WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL,
            10, 10, 100, 30,   // placeholder – real pos set in WM_SIZE
            hwnd, (HMENU)ID_EDIT_NAME, g_hInst, nullptr);
        {
            HFONT hf = CreateFontW(15, 0, 0, 0, FW_NORMAL, 0, 0, 0,
                DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_SWISS, L"Segoe UI");
            SendMessage(g_hEdit, WM_SETFONT, (WPARAM)hf, TRUE);
        }
        SetFocus(g_hEdit);
        return 0;

    case WM_SIZE:
        RepositionEdit(hwnd);
        InvalidateRect(hwnd, nullptr, TRUE);
        return 0;

    case WM_CTLCOLOREDIT: {
        HDC dc = (HDC)wp;
        SetBkColor  (dc, RGB(13, 17, 23));
        SetTextColor(dc, RGB(230, 237, 243));
        static HBRUSH hbEdit = CreateSolidBrush(RGB(13, 17, 23));
        return (LRESULT)hbEdit;
    }

    case WM_PAINT:
        PaintLogin(hwnd);
        return 0;

    case WM_ERASEBKGND:
        return TRUE;

    case WM_LBUTTONDOWN: {
        // Detect click on the "Get Started" button rect
        RECT rc; GetClientRect(hwnd, &rc);
        int W = rc.right, H = rc.bottom;
        int cw = 380, ch = 480;
        int cx = (W - cw) / 2, cy = (H - ch) / 2;
        int mx = GET_X_LPARAM(lp), my = GET_Y_LPARAM(lp);
        if (mx >= cx + 30 && mx <= cx + cw - 30 &&
            my >= cy + 274 && my <= cy + 322)
            OnLoginSubmit(hwnd);
        return 0;
    }

    case WM_DESTROY:
        if (!g_mainWnd || !IsWindowVisible(g_mainWnd))
            PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

// ════════════════════════════════════════════════════════════════════════════
//  MAIN WINDOW  — YouTube-style Dashboard
// ════════════════════════════════════════════════════════════════════════════

static void BuildCards(int W, int H) {
    g_cards.clear();
    // Layout zones
    const float HDR_H = 72.f;
    const float BNR_H = 78.f;
    const float SEC_H = 38.f;
    float top = HDR_H + BNR_H + SEC_H + 8.f;

    float pad = 28.f;
    float gap = 18.f;
    float cw  = ((float)W - pad * 2.f - gap * 2.f) / 3.f;
    float ch  = 190.f;

    float xs[3] = { pad, pad + cw + gap, pad + (cw + gap) * 2.f };
    float ys[2] = { top, top + ch + gap };

    const wchar_t* labels[6] = { L"\u25B6", L"\u2316", L"\u2261", L"\u26AF", L"\u2710", L"\u2630" };
    const wchar_t* titles[6] = { L"Start Bot",   L"Web Panel",   L"Live Logs",
                                  L"Manage URLs", L"Messages",    L"Settings"  };
    const wchar_t* descs[6]  = { L"Launch YouTube live chat bot",
                                  L"Open panel in browser (mobile-ready)",
                                  L"View real-time activity logs",
                                  L"Add / remove YouTube live URLs",
                                  L"Edit the chat messages library",
                                  L"Edit bot configuration (config.json)" };

    for (int i = 0; i < 6; i++) {
        Card c;
        c.x = xs[i % 3];  c.y = ys[i / 3];
        c.w = cw;          c.h = ch;
        c.label  = labels[i];
        c.title  = titles[i];
        c.desc   = descs[i];
        c.theme  = THEMES[i];
        c.action = i;
        c.hovered = false;
        g_cards.push_back(c);
    }
}

static void PaintCard(Graphics& g, const Card& c) {
    bool hov = c.hovered;

    // Shadow on hover
    if (hov) {
        SolidBrush shBr(Color(40, 0, 0, 0));
        FillRRect(g, &shBr, c.x + 3, c.y + 4, c.w, c.h, 10.f);
    }

    // Card body
    SolidBrush bgBr(hov ? Color(255, 28, 35, 44) : C_BG2);
    FillRRect(g, &bgBr, c.x, c.y, c.w, c.h);

    // Border
    Color borderCol = hov ? Color(255, 0, 200, 100) : C_BG3;
    Pen borderPen(borderCol, hov ? 1.5f : 1.f);
    BorderRRect(g, &borderPen, c.x, c.y, c.w, c.h);

    // Thumbnail gradient (top 108px, clipped to card corners)
    float th = 108.f;
    LinearGradientBrush thumbGr(
        PointF(c.x, c.y),
        PointF(c.x + c.w, c.y + th),
        c.theme.c1, c.theme.c2);
    // Clip path (rounded top + straight bottom)
    float r = 10.f;
    GraphicsPath clip;
    clip.AddArc(c.x,       c.y,       r*2, r*2, 180, 90);
    clip.AddArc(c.x+c.w-r*2, c.y,   r*2, r*2, 270, 90);
    clip.AddLine(c.x + c.w, c.y + th, c.x, c.y + th);
    clip.CloseFigure();
    g.SetClip(&clip);
    g.FillPath(&thumbGr, &clip);
    g.ResetClip();

    // Label / icon text centred on thumbnail
    Font iconFont(L"Segoe UI", 30, FontStyleBold, UnitPixel);
    SolidBrush wBr(Color(200, 255, 255, 255));
    Txt(g, c.label, &iconFont, &wBr,
        c.x, c.y, c.w, th, StringAlignmentCenter, StringAlignmentCenter);

    // Title
    Font titleF(L"Segoe UI", 13, FontStyleBold, UnitPixel);
    SolidBrush titleBr(hov ? C_GREEN : C_TEXT);
    Txt(g, c.title, &titleF, &titleBr,
        c.x + 12, c.y + th + 8, c.w - 40, 20);

    // Arrow hint on hover
    if (hov) {
        SolidBrush arBr(C_GREEN);
        Txt(g, L"\u2192", &titleF, &arBr,
            c.x + c.w - 28, c.y + th + 8, 22, 20);
    }

    // Description
    Font descF(L"Segoe UI", 10, FontStyleRegular, UnitPixel);
    SolidBrush mBr(C_MUTED);
    Txt(g, c.desc, &descF, &mBr,
        c.x + 12, c.y + th + 30, c.w - 24, 38,
        StringAlignmentNear, StringAlignmentNear, true);
}

static void PaintMain(HWND hwnd) {
    PAINTSTRUCT ps;
    HDC hdc = BeginPaint(hwnd, &ps);
    RECT rc; GetClientRect(hwnd, &rc);
    int W = rc.right, H = rc.bottom;

    HDC mdc = CreateCompatibleDC(hdc);
    HBITMAP bmp = CreateCompatibleBitmap(hdc, W, H);
    HBITMAP old = (HBITMAP)SelectObject(mdc, bmp);

    Graphics g(mdc);
    g.SetSmoothingMode(SmoothingModeAntiAlias);
    g.SetTextRenderingHint(TextRenderingHintClearTypeGridFit);

    // ── Background ──────────────────────────────────────────────
    SolidBrush bgBr(C_BG);
    g.FillRectangle(&bgBr, 0, 0, W, H);

    // ── YouTube-style Header (0–72) ─────────────────────────────
    LinearGradientBrush hdrGr(PointF(0, 0), PointF((float)W, 0), C_YTR1, C_YTR2);
    g.FillRectangle(&hdrGr, 0, 0, W, 72);

    // Header drop-shadow
    LinearGradientBrush hdrSh(PointF(0, 72), PointF(0, 84),
                               Color(90, 0, 0, 0), Color(0, 0, 0, 0));
    g.FillRectangle(&hdrSh, 0, 72, W, 12);

    // ▶ Logo
    SolidBrush wBr(C_TEXT);
    g.FillEllipse(&wBr, 18.f, 18.f, 36.f, 36.f);
    PointF tri[3] = {{26.f, 27.f}, {48.f, 36.f}, {26.f, 45.f}};
    SolidBrush redBr(C_YTR1);
    g.FillPolygon(&redBr, tri, 3);

    Font fAppName(L"Segoe UI", 22, FontStyleBold, UnitPixel);
    Font fAppSub (L"Segoe UI",  9, FontStyleRegular, UnitPixel);
    Font fSection(L"Segoe UI", 10, FontStyleBold, UnitPixel);
    Font fWelcome(L"Segoe UI", 17, FontStyleBold, UnitPixel);
    Font fWelSub (L"Segoe UI", 11, FontStyleRegular, UnitPixel);
    Font fStatus (L"Segoe UI",  9, FontStyleRegular, UnitPixel);

    Txt(g, L"AsifTechGlobal", &fAppName, &wBr, 62, 16, 260, 30);
    SolidBrush pinkBr(Color(255, 255, 200, 200));
    Txt(g, L"YouTube Live Bot System", &fAppSub, &pinkBr, 64, 46, 220, 18);

    // User badge (right side of header)
    float av_x = (float)(W - 200), av_y = 18.f;
    SolidBrush avBg(C_GBTN);
    g.FillEllipse(&avBg, av_x, av_y, 34.f, 34.f);
    Font avF(L"Segoe UI", 14, FontStyleBold, UnitPixel);
    std::wstring init(1, g_userName.empty() ? L'A' : (wchar_t)towupper(g_userName[0]));
    Txt(g, init.c_str(), &avF, &wBr, av_x, av_y, 34.f, 34.f,
        StringAlignmentCenter, StringAlignmentCenter);
    Font avNameF(L"Segoe UI", 13, FontStyleBold, UnitPixel);
    Font avRoleF(L"Segoe UI",  9, FontStyleRegular, UnitPixel);
    Txt(g, g_userName.c_str(), &avNameF, &wBr, av_x + 40, 22, 155, 22);
    Txt(g, L"Bot Operator", &avRoleF, &pinkBr, av_x + 41, 44, 150, 16);

    // ── Welcome Banner (72–150) ─────────────────────────────────
    SolidBrush bg2Br(C_BG2);
    g.FillRectangle(&bg2Br, 0, 72, W, 78);
    Pen borderP(C_BG3, 1.f);
    g.DrawLine(&borderP, 0, 149, W, 149);

    std::wstring welcome = std::wstring(L"\U0001F44B  Welcome back, ") + g_userName + L"!";
    SolidBrush gBr(C_GREEN);
    SolidBrush mBr(C_MUTED);
    Txt(g, welcome.c_str(), &fWelcome, &gBr, 28, 84, (float)(W - 56), 28);
    Txt(g, L"Your YouTube Live Chat Bot Dashboard  \u2022  Mobile-ready via Web Panel (same Wi-Fi)",
        &fWelSub, &mBr, 30, 116, (float)(W - 60), 20);

    // ── Section Title (150–188) ─────────────────────────────────
    SolidBrush secBr(C_MUTED);
    Txt(g, L"BOT CONTROLS", &fSection, &secBr, 30, 160, 180, 18);
    g.DrawLine(&borderP, 175, 169, (float)(W - 28), 169);

    // ── Cards ───────────────────────────────────────────────────
    for (const auto& c : g_cards)
        PaintCard(g, c);

    // ── Status Bar (bottom 28px) ────────────────────────────────
    g.FillRectangle(&bg2Br, 0, H - 28, W, 28);
    g.DrawLine(&borderP, 0, H - 28, W, H - 28);
    SolidBrush dimBr(Color(255, 72, 82, 95));
    std::wstring statusTxt =
        L"\u26A1 AsifTechGlobal  \u2022  Mobile URL: http://<PC-IP>:5000  "
        L"\u2022  User: " + g_userName;
    Txt(g, statusTxt.c_str(), &fStatus, &dimBr, 10, (float)(H - 21), (float)(W - 20), 16);

    BitBlt(hdc, 0, 0, W, H, mdc, 0, 0, SRCCOPY);
    SelectObject(mdc, old);
    DeleteObject(bmp);
    DeleteDC(mdc);
    EndPaint(hwnd, &ps);
}

LRESULT CALLBACK MainWndProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_SIZE: {
        RECT rc; GetClientRect(hwnd, &rc);
        BuildCards(rc.right, rc.bottom);
        InvalidateRect(hwnd, nullptr, TRUE);
        return 0;
    }
    case WM_PAINT:
        PaintMain(hwnd);
        return 0;

    case WM_ERASEBKGND:
        return TRUE;

    case WM_MOUSEMOVE: {
        int mx = GET_X_LPARAM(lp), my = GET_Y_LPARAM(lp);
        bool changed = false;
        bool onCard  = false;
        for (auto& c : g_cards) {
            bool nh = (mx >= (int)c.x && mx <= (int)(c.x + c.w) &&
                       my >= (int)c.y && my <= (int)(c.y + c.h));
            if (nh != c.hovered) { c.hovered = nh; changed = true; }
            if (nh) onCard = true;
        }
        if (changed) {
            SetCursor(LoadCursor(nullptr, onCard ? IDC_HAND : IDC_ARROW));
            InvalidateRect(hwnd, nullptr, FALSE);
        }
        return 0;
    }

    case WM_LBUTTONDOWN: {
        int mx = GET_X_LPARAM(lp), my = GET_Y_LPARAM(lp);
        for (auto& c : g_cards) {
            if (mx >= (int)c.x && mx <= (int)(c.x + c.w) &&
                my >= (int)c.y && my <= (int)(c.y + c.h)) {
                DoAction(c.action);
                break;
            }
        }
        return 0;
    }

    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

// ════════════════════════════════════════════════════════════════════════════
//  WINMAIN
// ════════════════════════════════════════════════════════════════════════════

int WINAPI wWinMain(HINSTANCE hInst, HINSTANCE, PWSTR, int) {
    g_hInst = hInst;

    // Get directory of this exe (same as the bot folder)
    GetModuleFileNameW(nullptr, g_dir, MAX_PATH);
    for (int i = (int)wcslen(g_dir) - 1; i >= 0; i--)
        if (g_dir[i] == L'\\') { g_dir[i] = L'\0'; break; }

    // ── GDI+ ──
    GdiplusStartupInput gsi;
    GdiplusStartup(&g_gdip, &gsi, nullptr);

    // ── Common Controls ──
    INITCOMMONCONTROLSEX ice = { sizeof(ice), ICC_STANDARD_CLASSES };
    InitCommonControlsEx(&ice);

    // ── Register windows ──
    {
        WNDCLASSEXW wc = { sizeof(wc) };
        wc.lpfnWndProc   = LoginWndProc;
        wc.hInstance     = hInst;
        wc.lpszClassName = L"ATG_Login";
        wc.hCursor       = LoadCursor(nullptr, IDC_ARROW);
        wc.hbrBackground = CreateSolidBrush(RGB(13, 17, 23));
        wc.hIcon         = LoadIcon(hInst, IDI_APPLICATION);
        RegisterClassExW(&wc);
    }
    {
        WNDCLASSEXW wc = { sizeof(wc) };
        wc.lpfnWndProc   = MainWndProc;
        wc.hInstance     = hInst;
        wc.lpszClassName = L"ATG_Main";
        wc.hCursor       = LoadCursor(nullptr, IDC_ARROW);
        wc.hbrBackground = CreateSolidBrush(RGB(13, 17, 23));
        wc.hIcon         = LoadIcon(hInst, IDI_APPLICATION);
        RegisterClassExW(&wc);
    }

    // ── Create Login window (centered) ──
    int sw = GetSystemMetrics(SM_CXSCREEN);
    int sh = GetSystemMetrics(SM_CYSCREEN);
    int lw = 500, lh = 580;
    g_loginWnd = CreateWindowExW(
        WS_EX_APPWINDOW,
        L"ATG_Login",
        L"AsifTechGlobal \u2014 YT Bot",
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
        (sw - lw) / 2, (sh - lh) / 2, lw, lh,
        nullptr, nullptr, hInst, nullptr);

    // ── Create Main window (hidden until login) ──
    g_mainWnd = CreateWindowExW(
        WS_EX_APPWINDOW,
        L"ATG_Main",
        L"AsifTechGlobal \u2014 YT Bot Dashboard",
        WS_OVERLAPPEDWINDOW,
        50, 50, 1140, 720,
        nullptr, nullptr, hInst, nullptr);

    // Pre-build cards at default size
    BuildCards(1140, 720);

    DarkTitle(g_loginWnd);
    DarkTitle(g_mainWnd);

    ShowWindow(g_loginWnd, SW_SHOW);
    UpdateWindow(g_loginWnd);

    // ── Message loop (intercepts Enter key for edit control) ──
    MSG message;
    while (GetMessageW(&message, nullptr, 0, 0)) {
        // Enter key → submit login
        if (message.message == WM_KEYDOWN && message.wParam == VK_RETURN &&
            g_loginWnd && IsWindowVisible(g_loginWnd))
        {
            OnLoginSubmit(g_loginWnd);
            continue;
        }
        TranslateMessage(&message);
        DispatchMessageW(&message);
    }

    GdiplusShutdown(g_gdip);
    return (int)message.wParam;
}
