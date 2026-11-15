using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;

/// Keyboard + gamepad input, polled once per frame. Keys and gamepad buttons are rebindable (Settings menu
/// in the menu bar) and saved between launches; Esc, Enter, R and Q keep their fixed jobs, and the stick
/// and D-pad always move.
public static class In
{
    public enum Act { Left, Right, Jump, Duck, Run, Fire, Pause, Count }
    public static readonly string[] ActNames = { "Move Left", "Move Right", "Jump", "Duck", "Run", "Fire", "Pause" };

    public static float X;
    public static bool JumpDown, JumpHeld, Run, FireDown, Down, Pause, Esc, Confirm, Restart, Quit;
    public static System.Action Bot;            // test hook: overrides input
    public static System.Action Changed;        // raised when a binding changes

    static readonly List<Key>[] keys = new List<Key>[(int)Act.Count];
    static readonly Key[][] defaults =
    {
        new[] { Key.A, Key.LeftArrow }, new[] { Key.D, Key.RightArrow }, new[] { Key.Space, Key.W, Key.UpArrow },
        new[] { Key.S, Key.DownArrow }, new[] { Key.LeftShift, Key.RightShift }, new[] { Key.X, Key.J }, new[] { Key.P },
    };
    // gamepad buttons per action (Left / Right stay on the stick and D-pad)
    static readonly List<GamepadButton>[] pad = new List<GamepadButton>[(int)Act.Count];
    static readonly GamepadButton[][] padDefaults =
    {
        new GamepadButton[0], new GamepadButton[0], new[] { GamepadButton.South }, new[] { GamepadButton.DpadDown },
        new[] { GamepadButton.West, GamepadButton.RightTrigger }, new[] { GamepadButton.East }, new[] { GamepadButton.Start },
    };
    static readonly GamepadButton[] padChoices =
    {
        GamepadButton.South, GamepadButton.East, GamepadButton.West, GamepadButton.North, GamepadButton.LeftShoulder, GamepadButton.RightShoulder,
        GamepadButton.LeftTrigger, GamepadButton.RightTrigger, GamepadButton.Start, GamepadButton.Select, GamepadButton.LeftStick, GamepadButton.RightStick,
        GamepadButton.DpadUp, GamepadButton.DpadDown,
    };
    static bool loaded;
    public static bool CapturingPad { get; private set; }
    public static bool PadConnected => Gamepad.current != null;
    public static bool Capturing { get; private set; }
    public static Act CaptureAct { get; private set; }

    static void Load()
    {
        loaded = true;
        for (int i = 0; i < keys.Length; i++)
        {
            keys[i] = new List<Key>();
            string saved = PlayerPrefs.GetString("bind_" + i, null);
            if (string.IsNullOrEmpty(saved)) { keys[i].AddRange(defaults[i]); continue; }
            foreach (var part in saved.Split(','))
                if (System.Enum.TryParse(part, out Key k) && k != Key.None) keys[i].Add(k);
        }
        for (int i = 0; i < pad.Length; i++)
        {
            pad[i] = new List<GamepadButton>();
            string saved = PlayerPrefs.GetString("pad_" + i, null);
            if (string.IsNullOrEmpty(saved)) { pad[i].AddRange(padDefaults[i]); continue; }
            foreach (var part in saved.Split(','))
                if (System.Enum.TryParse(part, out GamepadButton b)) pad[i].Add(b);
        }
    }

    static void Save()
    {
        for (int i = 0; i < keys.Length; i++) PlayerPrefs.SetString("bind_" + i, keys[i].Count == 0 ? "None" : string.Join(",", keys[i]));
        for (int i = 0; i < pad.Length; i++) PlayerPrefs.SetString("pad_" + i, pad[i].Count == 0 ? "None" : string.Join(",", pad[i]));
        PlayerPrefs.Save();
        Changed?.Invoke();
    }

    public static void ResetDefaults()
    {
        for (int i = 0; i < keys.Length; i++) { keys[i].Clear(); keys[i].AddRange(defaults[i]); PlayerPrefs.DeleteKey("bind_" + i); }
        PlayerPrefs.Save();
        Changed?.Invoke();
    }

    public static void ResetPadDefaults()
    {
        if (!loaded) Load();
        for (int i = 0; i < pad.Length; i++) { pad[i].Clear(); pad[i].AddRange(padDefaults[i]); PlayerPrefs.DeleteKey("pad_" + i); }
        PlayerPrefs.Save();
        Changed?.Invoke();
    }

    static string PadName(GamepadButton b)
    {
        switch (b)
        {
            case GamepadButton.South: return "A / ✕"; case GamepadButton.East: return "B / ○"; case GamepadButton.West: return "X / □"; case GamepadButton.North: return "Y / △";
            case GamepadButton.LeftShoulder: return "LB"; case GamepadButton.RightShoulder: return "RB"; case GamepadButton.LeftTrigger: return "LT"; case GamepadButton.RightTrigger: return "RT";
            case GamepadButton.Start: return "Start"; case GamepadButton.Select: return "Select"; case GamepadButton.LeftStick: return "L3"; case GamepadButton.RightStick: return "R3";
            case GamepadButton.DpadUp: return "D-pad ↑"; case GamepadButton.DpadDown: return "D-pad ↓";
        }
        return b.ToString();
    }

    /// Human-readable gamepad buttons for an action, e.g. "X / □  or  RT".
    public static string PadLabel(Act a)
    {
        if (!loaded) Load();
        var parts = new List<string>();
        foreach (var b in pad[(int)a]) parts.Add(PadName(b));
        return parts.Count == 0 ? "(not set)" : string.Join("  or  ", parts);
    }

    /// Human-readable keys for an action, e.g. "Space / W / ↑".
    public static string Label(Act a)
    {
        if (!loaded) Load();
        var kb = Keyboard.current; var parts = new List<string>();
        foreach (var k in keys[(int)a])
        {
            string n = k == Key.LeftArrow ? "←" : k == Key.RightArrow ? "→" : k == Key.UpArrow ? "↑" : k == Key.DownArrow ? "↓" : k == Key.Space ? "Space" :
                       k == Key.LeftShift ? "Left Shift" : k == Key.RightShift ? "Right Shift" : (kb != null ? kb[k].displayName : k.ToString());
            if (string.IsNullOrEmpty(n)) n = k.ToString();
            parts.Add(n.Length == 1 ? n.ToUpper() : n);
        }
        return parts.Count == 0 ? "(not set)" : string.Join(" / ", parts);
    }

    /// The next gamepad button pressed becomes the only button for this action (asked for by the Settings window).
    public static void BeginPadCapture(Act a) { if (!loaded) Load(); Capturing = true; CapturingPad = true; CaptureAct = a; }
    public static void CancelCapture() { Capturing = false; }

    /// Makes `k` the only key for an action (chosen in the Settings window); a key has one job at a time.
    public static void SetKey(Act a, Key k)
    {
        if (!loaded) Load();
        if (k == Key.None) return;
        for (int i = 0; i < keys.Length; i++) if (i != (int)a) keys[i].Remove(k);
        keys[(int)a].Clear(); keys[(int)a].Add(k);
        Save();
    }

    static bool PadHeld(Act a, Gamepad g) { foreach (var b in pad[(int)a]) if (g[b].isPressed) return true; return false; }
    static bool PadPressed(Act a, Gamepad g) { foreach (var b in pad[(int)a]) if (g[b].wasPressedThisFrame) return true; return false; }

    static bool Held(Act a, Keyboard k) { foreach (var key in keys[(int)a]) if (k[key].isPressed) return true; return false; }
    static bool Pressed(Act a, Keyboard k) { foreach (var key in keys[(int)a]) if (k[key].wasPressedThisFrame) return true; return false; }

    public static void Poll()
    {
        if (!loaded) Load();
        var k = Keyboard.current; var g = Gamepad.current;
        X = 0; JumpDown = JumpHeld = Run = FireDown = Down = Pause = Esc = Confirm = Restart = Quit = false;

        if (Capturing)
        {
            if (g == null) return;
            foreach (var b in padChoices)
            {
                if (!g[b].wasPressedThisFrame) continue;
                for (int i = 0; i < pad.Length; i++) if (i != (int)CaptureAct) pad[i].Remove(b);          // one job per button
                pad[(int)CaptureAct].Clear(); pad[(int)CaptureAct].Add(b);
                Capturing = false; Save();
                break;
            }
            return;
        }

        if (k != null)
        {
            if (Held(Act.Left, k)) X -= 1;
            if (Held(Act.Right, k)) X += 1;
            JumpDown |= Pressed(Act.Jump, k); JumpHeld |= Held(Act.Jump, k);
            Run |= Held(Act.Run, k);
            FireDown |= Pressed(Act.Fire, k);
            Down |= Held(Act.Duck, k);
            Pause |= Pressed(Act.Pause, k);
            Esc |= k.escapeKey.wasPressedThisFrame;
            Confirm |= k.enterKey.wasPressedThisFrame || k.numpadEnterKey.wasPressedThisFrame || k.spaceKey.wasPressedThisFrame || Pressed(Act.Jump, k);
            Restart |= k.rKey.wasPressedThisFrame;
            Quit |= k.qKey.wasPressedThisFrame;
        }
        if (g != null)
        {
            float sx = g.leftStick.x.ReadValue();
            if (Mathf.Abs(sx) > 0.3f) X += Mathf.Sign(sx);
            if (g.dpad.left.isPressed) X -= 1;
            if (g.dpad.right.isPressed) X += 1;
            JumpDown |= PadPressed(Act.Jump, g); JumpHeld |= PadHeld(Act.Jump, g);
            Run |= PadHeld(Act.Run, g);
            FireDown |= PadPressed(Act.Fire, g);
            Down |= PadHeld(Act.Duck, g) || g.leftStick.y.ReadValue() < -0.6f;
            Pause |= PadPressed(Act.Pause, g);
            Confirm |= g.buttonSouth.wasPressedThisFrame || g.startButton.wasPressedThisFrame || PadPressed(Act.Jump, g);
            Restart |= g.selectButton.wasPressedThisFrame && !PadHeld(Act.Pause, g);
        }
        X = Mathf.Clamp(X, -1, 1);
        Bot?.Invoke();
    }
}
