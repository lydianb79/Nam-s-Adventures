// Native macOS menu items and the Settings window.
//   <App menu> ▸ Settings…  (⌘,)  opens a window with four tabs: Display, Audio, Keyboard, Gamepad
//   View       ▸ Enter / Exit Full Screen (⌘F)
// Build:  clang -dynamiclib -fobjc-arc -framework Cocoa -arch arm64 -arch x86_64 -o Assets/Plugins/macOS/libNamMenu.dylib Tools/NamMenu.m
#import <Cocoa/Cocoa.h>

// kind: 0 fullscreen resolution (w,h) · 1 window size (w,h) · 2 toggle fullscreen · 3 render quality (w = percent)
//       4 rebind keyboard action w · 5 reset keyboard · 6 rebind gamepad action w · 7 reset gamepad
//       8 toggle start-in-fullscreen · 9 settings window opened
//       12 music volume (w = percent) · 13 effects volume (w = percent)
//       10 keyboard key chosen (w = action, h = macOS virtual key code) · 11 capture cancelled
typedef void (*NamCb)(int kind, int w, int h);
static NamCb gCb;
static NSMenuItem *gToggle;
static NSPanel *gPanel;
static NSPopUpButton *gFsPop, *gWinPop, *gQualPop;
static NSButton *gStartChk, *gKeyBtn[7], *gPadBtn[7];
static NSSlider *gMusicSl, *gFxSl; static int sMusicVol = 80, sFxVol = 100;
// last known state, so the window can be built lazily and still show the right values
static long long sFsTag = 0, sWinTag = 100000000LL + 1280 * 10000LL + 720, sQualTag = 3 * 100000000LL + 100 * 10000LL;
static int sStartFull = 1;
static NSString *sKeyTitle[7], *sPadTitle[7];
static int gCapKey = -1, gCapPad = -1;       // action currently waiting for a key / gamepad button, or -1
static id gMonitor;
static NSString *const kActions[7] = { @"Move Left", @"Move Right", @"Jump", @"Duck", @"Run", @"Fire", @"Pause" };

static long long tagFor(int kind, int w, int h) { return kind * 100000000LL + w * 10000LL + h; }
static void namSend(long long t) { if (gCb) gCb((int)(t / 100000000LL), (int)((t / 10000LL) % 10000LL), (int)(t % 10000LL)); }
static void applyState(void);
static void showSettings(void);
static void cancelCapture(void);

@interface NamMenuTarget : NSObject
@end
@implementation NamMenuTarget
- (void)pick:(NSMenuItem *)it { namSend(it.tag); }
- (void)popupPick:(NSPopUpButton *)p { namSend(p.selectedItem.tag); }
- (void)check:(NSButton *)b { namSend(b.tag); }
- (void)slide:(NSSlider *)sl { namSend(tagFor((int)sl.tag, (int)lround(sl.doubleValue), 0)); }
- (void)openSettings:(id)sender { showSettings(); }
- (void)rebind:(NSButton *)b
{
    // Everything happens in this window: the button waits for the next key (read here) or the next gamepad
    // button (read by the game, which keeps receiving gamepad input while this window is in front).
    BOOL wasThis = (b == (gCapKey >= 0 ? gKeyBtn[gCapKey] : nil)) || (b == (gCapPad >= 0 ? gPadBtn[gCapPad] : nil));
    if (gCapKey >= 0 || gCapPad >= 0) { gCapKey = gCapPad = -1; namSend(tagFor(11, 0, 0)); applyState(); if (wasThis) return; }
    int kind = (int)(b.tag / 100000000LL), action = (int)((b.tag / 10000LL) % 10000LL);
    if (kind == 4) { gCapKey = action; b.title = @"Press a key…  (Esc cancels)"; }
    else { gCapPad = action; b.title = @"Press a gamepad button…  (Esc cancels)"; namSend(b.tag); }
    [gPanel makeFirstResponder:nil];
    [gPanel makeKeyAndOrderFront:nil];          // make sure the next key press comes to this window
}
@end
static NamMenuTarget *gTarget;

static NSTextField *addLabel(NSView *v, NSString *s, NSRect f, BOOL bold, BOOL small)
{
    NSTextField *t = [NSTextField labelWithString:s]; t.frame = f;
    t.font = bold ? [NSFont boldSystemFontOfSize:13] : [NSFont systemFontOfSize:small ? 11 : 13];
    if (small) t.textColor = [NSColor secondaryLabelColor];
    [v addSubview:t]; return t;
}
static NSPopUpButton *addPopup(NSView *v, NSRect f)
{
    NSPopUpButton *p = [[NSPopUpButton alloc] initWithFrame:f pullsDown:NO];
    p.target = gTarget; p.action = @selector(popupPick:); [v addSubview:p]; return p;
}
static void popItem(NSPopUpButton *p, NSString *title, int kind, int w, int h) { [p addItemWithTitle:title]; p.lastItem.tag = tagFor(kind, w, h); }
static NSButton *addButton(NSView *v, NSString *title, NSRect f, SEL action, long long tag)
{
    NSButton *b = [NSButton buttonWithTitle:title target:gTarget action:action]; b.frame = f; b.tag = tag; [v addSubview:b]; return b;
}

static void buildPanel(void)
{
    const CGFloat W = 520, H = 440;
    gPanel = [[NSPanel alloc] initWithContentRect:NSMakeRect(0, 0, W, H) styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable) backing:NSBackingStoreBuffered defer:NO];
    gPanel.title = @"Settings";
    [[NSNotificationCenter defaultCenter] addObserverForName:NSWindowWillCloseNotification object:gPanel queue:nil usingBlock:^(NSNotification *n) { cancelCapture(); }]; gPanel.releasedWhenClosed = NO; gPanel.hidesOnDeactivate = NO; gPanel.floatingPanel = YES;
    gPanel.collectionBehavior = NSWindowCollectionBehaviorFullScreenAuxiliary | NSWindowCollectionBehaviorMoveToActiveSpace;
    NSTabView *tabs = [[NSTabView alloc] initWithFrame:NSMakeRect(12, 12, W - 24, H - 24)];
    [gPanel.contentView addSubview:tabs];
    const CGFloat TW = W - 60, TH = H - 90;

    // ---- Display
    NSView *d = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, TW, TH)];
    CGFloat y = TH - 44;
    addLabel(d, @"Fullscreen resolution", NSMakeRect(20, y, 180, 20), NO, NO);
    gFsPop = addPopup(d, NSMakeRect(210, y - 4, 230, 26));
    popItem(gFsPop, @"Native (display resolution)", 0, 0, 0); popItem(gFsPop, @"3840 × 2160", 0, 3840, 2160); popItem(gFsPop, @"2560 × 1440", 0, 2560, 1440);
    popItem(gFsPop, @"1920 × 1080", 0, 1920, 1080); popItem(gFsPop, @"1600 × 900", 0, 1600, 900); popItem(gFsPop, @"1280 × 720", 0, 1280, 720);
    y -= 44;
    addLabel(d, @"Window size", NSMakeRect(20, y, 180, 20), NO, NO);
    gWinPop = addPopup(d, NSMakeRect(210, y - 4, 230, 26));
    popItem(gWinPop, @"1920 × 1080", 1, 1920, 1080); popItem(gWinPop, @"1600 × 900", 1, 1600, 900); popItem(gWinPop, @"1280 × 720", 1, 1280, 720); popItem(gWinPop, @"960 × 540", 1, 960, 540);
    y -= 44;
    addLabel(d, @"Render quality", NSMakeRect(20, y, 180, 20), NO, NO);
    gQualPop = addPopup(d, NSMakeRect(210, y - 4, 230, 26));
    popItem(gQualPop, @"Ultra (2× supersampled)", 3, 200, 0); popItem(gQualPop, @"Sharp (1.5× supersampled)", 3, 150, 0); popItem(gQualPop, @"Standard", 3, 100, 0); popItem(gQualPop, @"Fast (0.75×)", 3, 75, 0);
    addLabel(d, @"Supersampling is sharper and steadier but heavier on the graphics chip.", NSMakeRect(20, y - 30, TW - 40, 16), NO, YES);
    y -= 80;
    gStartChk = [NSButton checkboxWithTitle:@"Start in full screen" target:gTarget action:@selector(check:)];
    gStartChk.frame = NSMakeRect(18, y, 300, 22); gStartChk.tag = tagFor(8, 0, 0); [d addSubview:gStartChk];
    addLabel(d, @"Switch at any time with View ▸ Enter Full Screen (⌘F); Esc leaves full screen.", NSMakeRect(20, y - 24, TW - 40, 16), NO, YES);
    NSTabViewItem *ti = [[NSTabViewItem alloc] initWithIdentifier:@"display"]; ti.label = @"Display"; ti.view = d; [tabs addTabViewItem:ti];

    // ---- Audio
    NSView *au = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, TW, TH)];
    CGFloat ay = TH - 50;
    addLabel(au, @"Music volume", NSMakeRect(20, ay, 150, 20), NO, NO);
    gMusicSl = [NSSlider sliderWithValue:sMusicVol minValue:0 maxValue:100 target:gTarget action:@selector(slide:)]; gMusicSl.frame = NSMakeRect(180, ay - 2, 260, 24); gMusicSl.tag = 12; gMusicSl.continuous = YES; [au addSubview:gMusicSl];
    ay -= 48;
    addLabel(au, @"Effects volume", NSMakeRect(20, ay, 150, 20), NO, NO);
    gFxSl = [NSSlider sliderWithValue:sFxVol minValue:0 maxValue:100 target:gTarget action:@selector(slide:)]; gFxSl.frame = NSMakeRect(180, ay - 2, 260, 24); gFxSl.tag = 13; gFxSl.continuous = YES; [au addSubview:gFxSl];
    addLabel(au, @"Effects include footsteps, enemies, fireworks and the cheering crowd.", NSMakeRect(20, ay - 34, TW - 40, 16), NO, YES);
    NSTabViewItem *ta = [[NSTabViewItem alloc] initWithIdentifier:@"audio"]; ta.label = @"Audio"; ta.view = au; [tabs addTabViewItem:ta];

    // ---- Keyboard / Gamepad
    for (int pad = 0; pad < 2; pad++)
    {
        NSView *v = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, TW, TH)];
        addLabel(v, pad ? @"Click a button below, then press the gamepad button to use. The stick and D-pad always move."
                        : @"Click a button below, then press the key to use. Esc cancels.", NSMakeRect(20, TH - 34, TW - 40, 16), NO, YES);
        CGFloat yy = TH - 74;
        for (int i = pad ? 2 : 0; i < 7; i++)
        {
            addLabel(v, kActions[i], NSMakeRect(20, yy, 150, 20), NO, NO);
            NSString *t = (pad ? sPadTitle[i] : sKeyTitle[i]) ?: @"…";
            NSButton *b = addButton(v, t, NSMakeRect(180, yy - 5, 260, 30), @selector(rebind:), tagFor(pad ? 6 : 4, i, 0));
            if (pad) gPadBtn[i] = b; else gKeyBtn[i] = b;
            yy -= 38;
        }
        addButton(v, @"Reset to Defaults", NSMakeRect(180, 14, 180, 30), @selector(check:), tagFor(pad ? 7 : 5, 0, 0));
        NSTabViewItem *t2 = [[NSTabViewItem alloc] initWithIdentifier:(pad ? @"gamepad" : @"keyboard")]; t2.label = pad ? @"Gamepad" : @"Keyboard"; t2.view = v; [tabs addTabViewItem:t2];
    }
    [gPanel center];
    applyState();
    // key presses while a button is waiting are taken here and never reach the game
    gMonitor = [NSEvent addLocalMonitorForEventsMatchingMask:(NSEventMaskKeyDown | NSEventMaskFlagsChanged) handler:^NSEvent *(NSEvent *e) {
        if (gCapKey < 0 && gCapPad < 0) return e;
        unsigned short code = e.keyCode;
        if (e.type == NSEventTypeFlagsChanged)
        {
            NSEventModifierFlags f = e.modifierFlags;
            BOOL down = ((code == 56 || code == 60) && (f & NSEventModifierFlagShift)) || ((code == 59 || code == 62) && (f & NSEventModifierFlagControl)) || ((code == 58 || code == 61) && (f & NSEventModifierFlagOption));
            if (!down || gCapKey < 0) return e;
        }
        if (code == 53) { gCapKey = gCapPad = -1; namSend(tagFor(11, 0, 0)); applyState(); return nil; }      // Esc cancels
        if (gCapKey >= 0) { int a = gCapKey; gCapKey = -1; namSend(tagFor(10, a, code)); applyState(); }
        return nil;
    }];
}

static void applyState(void)
{
    if (!gPanel) return;
    [gFsPop selectItemWithTag:sFsTag]; [gWinPop selectItemWithTag:sWinTag]; [gQualPop selectItemWithTag:sQualTag];
    gStartChk.state = sStartFull ? NSControlStateValueOn : NSControlStateValueOff;
    gMusicSl.doubleValue = sMusicVol; gFxSl.doubleValue = sFxVol;
    for (int i = 0; i < 7; i++)
    {
        if (gKeyBtn[i] && sKeyTitle[i] && i != gCapKey) gKeyBtn[i].title = sKeyTitle[i];     // a waiting button keeps its "Press…" prompt
        if (gPadBtn[i] && sPadTitle[i] && i != gCapPad) gPadBtn[i].title = sPadTitle[i];
    }
}

static void cancelCapture(void)
{
    if (gCapKey < 0 && gCapPad < 0) return;
    gCapKey = gCapPad = -1; namSend(tagFor(11, 0, 0)); applyState();
}

static void showSettings(void)
{
    if (!gPanel) buildPanel();
    applyState();
    [NSApp activateIgnoringOtherApps:YES];
    [gPanel makeKeyAndOrderFront:nil];
    namSend(tagFor(9, 0, 0));
}

void NamMenu_Install(NamCb cb)
{
    gCb = cb;
    dispatch_async(dispatch_get_main_queue(), ^{
        if (gTarget) return;
        gTarget = [NamMenuTarget new];
        NSMenu *mainMenu = [NSApp mainMenu];
        if (!mainMenu) { mainMenu = [[NSMenu alloc] initWithTitle:@"Main"]; [NSApp setMainMenu:mainMenu]; }

        // one "Settings…" item in the application menu, where Mac apps keep it
        NSMenu *appMenu = mainMenu.numberOfItems > 0 ? [mainMenu itemAtIndex:0].submenu : nil;
        if (!appMenu) { NSMenuItem *a = [[NSMenuItem alloc] initWithTitle:@"" action:nil keyEquivalent:@""]; appMenu = [[NSMenu alloc] initWithTitle:@""]; a.submenu = appMenu; [mainMenu insertItem:a atIndex:0]; }
        NSMenuItem *s = [[NSMenuItem alloc] initWithTitle:@"Settings…" action:@selector(openSettings:) keyEquivalent:@","];
        s.target = gTarget;
        [appMenu insertItem:s atIndex:0];
        [appMenu insertItem:[NSMenuItem separatorItem] atIndex:1];

        // View ▸ fullscreen toggle
        NSMenuItem *vTop = [[NSMenuItem alloc] initWithTitle:@"View" action:nil keyEquivalent:@""];
        NSMenu *view = [[NSMenu alloc] initWithTitle:@"View"]; vTop.submenu = view;
        [mainMenu insertItem:vTop atIndex:MIN(1, mainMenu.numberOfItems)];
        gToggle = [[NSMenuItem alloc] initWithTitle:@"Exit Full Screen" action:@selector(pick:) keyEquivalent:@"f"];
        gToggle.target = gTarget; gToggle.tag = tagFor(2, 0, 0); [view addItem:gToggle];
    });
}

void NamMenu_ShowSettings(void) { dispatch_async(dispatch_get_main_queue(), ^{ showSettings(); }); }

void NamMenu_SetState(int fsW, int fsH, int winW, int winH, int isFull)
{
    dispatch_async(dispatch_get_main_queue(), ^{
        sFsTag = tagFor(0, fsW, fsH); sWinTag = tagFor(1, winW, winH);
        gToggle.title = isFull ? @"Exit Full Screen" : @"Enter Full Screen";
        applyState();
    });
}

// Points -> pixels factor of the main display (2 on Retina), so window sizes can be given in points.
float NamMenu_BackingScale(void)
{
    NSScreen *sc = [NSScreen mainScreen];
    return sc ? (float)sc.backingScaleFactor : 1.0f;
}

void NamMenu_SetQuality(int percent) { dispatch_async(dispatch_get_main_queue(), ^{ sQualTag = tagFor(3, percent, 0); applyState(); }); }
void NamMenu_SetStartFull(int on) { dispatch_async(dispatch_get_main_queue(), ^{ sStartFull = on; applyState(); }); }

// Text on one action's button: pad = 0 keyboard, 1 gamepad.
void NamMenu_SetControl(int pad, int action, const char *title)
{
    NSString *t = title ? [NSString stringWithUTF8String:title] : @"";
    dispatch_async(dispatch_get_main_queue(), ^{
        if (action < 0 || action >= 7) return;
        if (pad) { sPadTitle[action] = t; if (gCapPad == action) gCapPad = -1; } else sKeyTitle[action] = t;
        applyState();
    });
}

void NamMenu_SetAudio(int music, int fx) { dispatch_async(dispatch_get_main_queue(), ^{ sMusicVol = music; sFxVol = fx; if (gPanel) { gMusicSl.doubleValue = music; gFxSl.doubleValue = fx; } }); }
