using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;

/// Bridge to the native macOS Settings window (app menu ▸ Settings…) and the View menu (Tools/NamMenu.m) + the display-mode logic behind it.
public static class NativeMenu
{
    delegate void Cb(int kind, int w, int h);
    [DllImport("NamMenu")] static extern void NamMenu_Install(Cb cb);
    [DllImport("NamMenu")] static extern void NamMenu_SetState(int fsW, int fsH, int winW, int winH, int isFull);
    [DllImport("NamMenu")] static extern float NamMenu_BackingScale();
    [DllImport("NamMenu")] static extern void NamMenu_SetQuality(int percent);
    [DllImport("NamMenu")] static extern void NamMenu_SetStartFull(int on);
    [DllImport("NamMenu")] static extern void NamMenu_ShowSettings();
    [DllImport("NamMenu")] static extern void NamMenu_SetAudio(int music, int fx);
    public static System.Action SettingsOpened;      // raised when the Settings window appears
    static float padHintT, fxPreviewT;
    // macOS virtual key code -> Input System key (both describe physical key positions)
    static readonly Dictionary<int, UnityEngine.InputSystem.Key> macKeys = BuildMacKeys();
    static Dictionary<int, UnityEngine.InputSystem.Key> BuildMacKeys()
    {
        var K = new Dictionary<int, UnityEngine.InputSystem.Key>();
        string[] names =
        {
            "0:A", "1:S", "2:D", "3:F", "4:H", "5:G", "6:Z", "7:X", "8:C", "9:V", "11:B", "12:Q", "13:W", "14:E", "15:R", "16:Y", "17:T",
            "18:Digit1", "19:Digit2", "20:Digit3", "21:Digit4", "22:Digit6", "23:Digit5", "24:Equals", "25:Digit9", "26:Digit7", "27:Minus", "28:Digit8", "29:Digit0",
            "30:RightBracket", "31:O", "32:U", "33:LeftBracket", "34:I", "35:P", "36:Enter", "37:L", "38:J", "39:Quote", "40:K", "41:Semicolon", "42:Backslash",
            "43:Comma", "44:Slash", "45:N", "46:M", "47:Period", "48:Tab", "49:Space", "50:Backquote", "51:Backspace",
            "56:LeftShift", "57:CapsLock", "58:LeftAlt", "59:LeftCtrl", "60:RightShift", "61:RightAlt", "62:RightCtrl",
            "65:NumpadPeriod", "67:NumpadMultiply", "69:NumpadPlus", "75:NumpadDivide", "76:NumpadEnter", "78:NumpadMinus",
            "82:Numpad0", "83:Numpad1", "84:Numpad2", "85:Numpad3", "86:Numpad4", "87:Numpad5", "88:Numpad6", "89:Numpad7", "91:Numpad8", "92:Numpad9",
            "96:F5", "97:F6", "98:F7", "99:F3", "100:F8", "101:F9", "103:F11", "109:F10", "111:F12", "118:F4", "120:F2", "122:F1",
            "115:Home", "116:PageUp", "117:Delete", "119:End", "121:PageDown", "123:LeftArrow", "124:RightArrow", "125:DownArrow", "126:UpArrow",
        };
        foreach (var n in names)
        {
            var p = n.Split(':');
            if (System.Enum.TryParse(p[1], out UnityEngine.InputSystem.Key key)) K[int.Parse(p[0])] = key;
        }
        return K;
    }
    [DllImport("NamMenu")] static extern void NamMenu_SetControl(int pad, int action, string title);
    static Cb keep;
    static int lastFull = -1;
    static readonly Queue<(int, int, int)> queue = new Queue<(int, int, int)>();
    static bool installed;

    [AOT.MonoPInvokeCallback(typeof(Cb))]
    static void OnPick(int kind, int w, int h) { lock (queue) queue.Enqueue((kind, w, h)); }

    public static void Install()
    {
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
        try { keep = OnPick; NamMenu_Install(keep); installed = true; }
        catch (System.Exception e) { Debug.LogWarning("Settings menu unavailable: " + e.Message); }
#endif
        Refresh();
        RefreshStartFull();
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
        if (installed) NamMenu_SetAudio(PlayerPrefs.GetInt("volMusic", 80), PlayerPrefs.GetInt("volFx", 100));
#endif
        In.Changed += RefreshControls;
        RefreshControls();
    }

    /// Writes the current key for every action into the Controls menu.
    public static void RefreshControls()
    {
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
        if (!installed) return;
        for (int i = 0; i < (int)In.Act.Count; i++) NamMenu_SetControl(0, i, In.Label((In.Act)i));
        for (int i = 2; i < (int)In.Act.Count; i++) NamMenu_SetControl(1, i, In.PadLabel((In.Act)i));
#endif
    }

    static int FsW => PlayerPrefs.GetInt("fsW", 0);
    static int FsH => PlayerPrefs.GetInt("fsH", 0);
    static int WinW => PlayerPrefs.GetInt("winW", 1280);
    static int WinH => PlayerPrefs.GetInt("winH", 720);

    /// Render quality: the scene is drawn at this fraction of the screen resolution, then scaled to fit.
    /// Above 100 % is supersampling (sharper, calmer grass, heavier); below is faster.
    public static int RenderPercent => PlayerPrefs.GetInt("renderPct", 100);
    public static void ApplyRenderScale()
    {
        var asset = UnityEngine.Rendering.Universal.UniversalRenderPipeline.asset;
        if (asset != null) asset.renderScale = Mathf.Clamp(RenderPercent / 100f, 0.5f, 2f);
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
        if (installed) NamMenu_SetQuality(RenderPercent);
#endif
    }

    /// Whether the game opens in fullscreen (Settings ▸ Display). On by default.
    public static bool StartFullscreen => PlayerPrefs.GetInt("startFull", 1) != 0;
    static void RefreshStartFull()
    {
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
        if (installed) NamMenu_SetStartFull(StartFullscreen ? 1 : 0);
#endif
    }

    public static void GoFullscreen()
    {
        int w = FsW, h = FsH;
        if (w <= 0 || h <= 0) { w = Display.main.systemWidth; h = Display.main.systemHeight; }
        Screen.SetResolution(w, h, FullScreenMode.FullScreenWindow);
        Refresh(true);
    }

    public static void GoWindowed()
    {
        // menu sizes are in points; Unity wants pixels (2x on Retina). Keep the window inside the display.
        float sc = 1f;
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
        try { sc = Mathf.Max(1f, NamMenu_BackingScale()); } catch (System.Exception) { }
#endif
        float fit = Mathf.Min(1f, Mathf.Min(Display.main.systemWidth * 0.94f / (WinW * sc), Display.main.systemHeight * 0.86f / (WinH * sc)));
        Screen.SetResolution(Mathf.RoundToInt(WinW * sc * fit), Mathf.RoundToInt(WinH * sc * fit), FullScreenMode.Windowed);
        Refresh(false);
    }

    static void Refresh(bool? full = null)
    {
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
        if (installed) NamMenu_SetState(FsW, FsH, WinW, WinH, (full ?? Screen.fullScreen) ? 1 : 0);
#endif
    }

    /// Applies menu choices on the main thread; call every frame.
    public static void Pump()
    {
        if (padHintT > 0) { padHintT -= Time.unscaledDeltaTime; if (padHintT <= 0) RefreshControls(); }
        int nowFull = Screen.fullScreen ? 1 : 0;
        if (nowFull != lastFull) { lastFull = nowFull; Refresh(); }      // keeps "Enter / Exit Full Screen" in sync
        while (true)
        {
            (int kind, int w, int h) e;
            lock (queue) { if (queue.Count == 0) break; e = queue.Dequeue(); }
            bool full = Screen.fullScreen;
            if (e.kind == 0) { PlayerPrefs.SetInt("fsW", e.w); PlayerPrefs.SetInt("fsH", e.h); if (full) GoFullscreen(); else Refresh(); }
            else if (e.kind == 1) { PlayerPrefs.SetInt("winW", e.w); PlayerPrefs.SetInt("winH", e.h); if (!full) GoWindowed(); else Refresh(); }
            else if (e.kind == 2) { if (full) GoWindowed(); else GoFullscreen(); }
            else if (e.kind == 3) { PlayerPrefs.SetInt("renderPct", e.w); ApplyRenderScale(); }
            else if (e.kind == 10 && e.w >= 0 && e.w < (int)In.Act.Count)
            {   // a key picked in the Settings window
                if (macKeys.TryGetValue(e.h, out var key)) In.SetKey((In.Act)e.w, key); else RefreshControls();
            }
            else if (e.kind == 11) { In.CancelCapture(); RefreshControls(); }
            else if (e.kind == 5) In.ResetDefaults();
            else if (e.kind == 6 && e.w >= 2 && e.w < (int)In.Act.Count)
            {   // the Settings window is waiting for a gamepad button; the game listens for it
                if (In.PadConnected) In.BeginPadCapture((In.Act)e.w);
                else
                {
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
                    NamMenu_SetControl(1, e.w, "No gamepad connected");
#endif
                    padHintT = 2f;
                }
            }
            else if (e.kind == 7) In.ResetPadDefaults();
            else if (e.kind == 8) { PlayerPrefs.SetInt("startFull", StartFullscreen ? 0 : 1); RefreshStartFull(); }
            else if (e.kind == 9) SettingsOpened?.Invoke();
            else if (e.kind == 12) { PlayerPrefs.SetInt("volMusic", e.w); Sfx.MusicVolume = e.w / 100f; }
            else if (e.kind == 13) { PlayerPrefs.SetInt("volFx", e.w); Sfx.FxVolume = e.w / 100f; if (Time.unscaledTime > fxPreviewT) { fxPreviewT = Time.unscaledTime + 0.25f; Sfx.Play("sfx_coin", 0.5f); } }
            PlayerPrefs.Save();
        }
    }
}
