#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

static NSString *const kDevDir = @"/Users/jerryli/Documents/deepseek-harness/default-workspace/code";

static NSString *SupportDir(void) {
    NSString *p = [@"~/Library/Application Support/AnimeBar" stringByExpandingTildeInPath];
    [[NSFileManager defaultManager] createDirectoryAtPath:p withIntermediateDirectories:YES attributes:nil error:nil];
    return p;
}

static NSString *ResPath(NSString *name) {
    NSString *p = [[[NSBundle mainBundle] resourcePath] stringByAppendingPathComponent:name];
    return [[NSFileManager defaultManager] fileExistsAtPath:p] ? p : nil;
}

@interface AppDelegate : NSObject <NSApplicationDelegate, WKScriptMessageHandler>
@property (strong) NSStatusItem *statusItem;
@property (strong) NSPopover *popover;
@property (strong) WKWebView *web;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)note {
    self.statusItem = [[NSStatusBar systemStatusBar] statusItemWithLength:NSVariableStatusItemLength];
    NSStatusBarButton *b = self.statusItem.button;
    NSImage *icon = [NSImage imageNamed:@"MenuIcon"];
    if (icon == nil) {
        NSString *iconPath = [[NSBundle mainBundle] pathForResource:@"MenuIcon" ofType:@"png"];
        if (iconPath) icon = [[NSImage alloc] initWithContentsOfFile:iconPath];
    }
    if (icon != nil) {
        [icon setTemplate:YES];
        [icon setSize:NSMakeSize(18, 18)];
        b.image = icon;
        b.imagePosition = NSImageOnly;
    } else {
        b.title = @"番";
    }
    b.font = [NSFont systemFontOfSize:13 weight:NSFontWeightMedium];
    b.target = self;
    b.action = @selector(clicked:);
    [b sendActionOn:(NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp)];

    self.popover = [NSPopover new];
    self.popover.behavior = NSPopoverBehaviorApplicationDefined;
    self.popover.contentSize = NSMakeSize(1080, 720);

    NSViewController *vc = [NSViewController new];
    WKWebViewConfiguration *cfg = [[WKWebViewConfiguration alloc] init];
    [cfg.userContentController addScriptMessageHandler:self name:@"anich"];
    [cfg.userContentController addScriptMessageHandler:self name:@"openurl"];
    self.web = [[WKWebView alloc] initWithFrame:NSMakeRect(0, 0, 1080, 720) configuration:cfg];
    vc.view = self.web;
    self.popover.contentViewController = vc;
}

- (void)clicked:(id)sender {
    NSEvent *e = [NSApp currentEvent];
    if (e != nil && e.type == NSEventTypeRightMouseUp) {
        [self showMenu];
        return;
    }
    [self toggle];
}

- (void)toggle {
    if (self.popover.shown) {
        [self.popover performClose:nil];
        return;
    }
    [self load];
    [self.popover showRelativeToRect:self.statusItem.button.bounds
                              ofView:self.statusItem.button
                       preferredEdge:NSRectEdgeMinY];
    // 必须真正激活 App，输入法候选窗才会跟随显示
    [[NSRunningApplication currentApplication]
        activateWithOptions:NSApplicationActivateAllWindows | NSApplicationActivateIgnoringOtherApps];
    [NSApp activateIgnoringOtherApps:YES];
    for (NSNumber *delay in @[@0.0, @0.15, @0.4]) {
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(delay.doubleValue * NSEC_PER_SEC)),
                       dispatch_get_main_queue(), ^{
            NSWindow *w = self.web.window ?: self.popover.contentViewController.view.window;
            if (w == nil) return;
            [w setLevel:NSFloatingWindowLevel];
            [w makeKeyAndOrderFront:nil];
            [w makeFirstResponder:self.web];
            [self.web.window makeFirstResponder:self.web];
        });
    }
}

- (NSString *)htmlPath {
    NSString *s = [SupportDir() stringByAppendingPathComponent:@"anime_board.html"];
    if ([[NSFileManager defaultManager] fileExistsAtPath:s]) return s;
    NSString *b = ResPath(@"anime_board.html");
    if (b) return b;
    return [kDevDir stringByAppendingPathComponent:@"anime_board.html"];
}

- (NSString *)scriptPath {
    NSString *s = [SupportDir() stringByAppendingPathComponent:@"anime_board.py"];
    if ([[NSFileManager defaultManager] fileExistsAtPath:s]) return s;
    NSString *b = ResPath(@"anime_board.py");
    if (b) return b;
    return [kDevDir stringByAppendingPathComponent:@"anime_board.py"];
}

- (void)prepareSupport {
    // 首次运行：把脚本和占位图复制到可写目录，之后生成都写在这里
    NSString *dir = SupportDir();
    NSFileManager *fm = [NSFileManager defaultManager];
    NSString *script = [dir stringByAppendingPathComponent:@"anime_board.py"];
    if (![fm fileExistsAtPath:script]) {
        NSString *b = ResPath(@"anime_board.py");
        if (b) [fm copyItemAtPath:b toPath:script error:nil];
    }
    NSString *assets = [dir stringByAppendingPathComponent:@"assets"];
    if (![fm fileExistsAtPath:assets]) {
        NSString *b = [[[NSBundle mainBundle] resourcePath] stringByAppendingPathComponent:@"assets"];
        if (b && [fm fileExistsAtPath:b]) [fm copyItemAtPath:b toPath:assets error:nil];
    }
}

- (void)load {
    [self prepareSupport];
    NSURL *u = [NSURL fileURLWithPath:[self htmlPath]];
    [self.web loadFileURL:u allowingReadAccessToURL:[u URLByDeletingLastPathComponent]];
}

- (void)showMenu {
    NSMenu *m = [[NSMenu alloc] init];
    NSMenuItem *i1 = [[NSMenuItem alloc] initWithTitle:@"刷新" action:@selector(doRefresh) keyEquivalent:@"r"];
    NSMenuItem *i2 = [[NSMenuItem alloc] initWithTitle:@"更新数据（重新抓取）" action:@selector(doUpdate) keyEquivalent:@"u"];
    NSMenuItem *i3 = [[NSMenuItem alloc] initWithTitle:@"用浏览器打开" action:@selector(doBrowser) keyEquivalent:@""];
    NSMenuItem *i3b = [[NSMenuItem alloc] initWithTitle:@"打开 AniCh" action:@selector(doAniCh) keyEquivalent:@""];
    NSMenuItem *i4 = [[NSMenuItem alloc] initWithTitle:@"退出" action:@selector(doQuit) keyEquivalent:@"q"];
    for (NSMenuItem *i in @[i1, i2, i3, i3b, i4]) { i.target = self; }
    [m addItem:i1];
    [m addItem:i2];
    [m addItem:[NSMenuItem separatorItem]];
    [m addItem:i3];
    [m addItem:i3b];
    [m addItem:[NSMenuItem separatorItem]];
    [m addItem:i4];
    self.statusItem.menu = m;
    [self.statusItem.button performClick:nil];
    self.statusItem.menu = nil;
}

- (void)doRefresh { [self load]; }

- (void)userContentController:(WKUserContentController *)ucc didReceiveScriptMessage:(WKScriptMessage *)msg {
    if ([msg.name isEqualToString:@"openurl"]) {
        NSString *u = [msg.body isKindOfClass:[NSString class]] ? msg.body : [msg.body description];
        if (u.length) {
            NSURL *url = [NSURL URLWithString:u];
            if (url) [[NSWorkspace sharedWorkspace] openURL:url];
        }
        return;
    }
    if (![msg.name isEqualToString:@"anich"]) return;
    NSString *title = [msg.body isKindOfClass:[NSString class]] ? msg.body : [msg.body description];
    if (title.length == 0) return;
    NSPasteboard *pb = [NSPasteboard generalPasteboard];
    [pb clearContents];
    [pb setString:title forType:NSPasteboardTypeString];
    [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:@"/Applications/anich.app"]];
    __weak typeof(self) weakSelf = self;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(1.5 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        [weakSelf pasteIntoAniCh];
    });
}

- (void)pasteIntoAniCh {
    NSString *src = @"tell application \"System Events\"\n"
                     "  tell process \"anich\"\n"
                     "    set frontmost to true\n"
                     "    delay 0.2\n"
                     "    keystroke \"v\" using command down\n"
                     "  end tell\n"
                     "end tell";
    NSAppleScript *sa = [[NSAppleScript alloc] initWithSource:src];
    [sa executeAndReturnError:nil];
}

- (void)doAniCh {
    [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:@"/Applications/anich.app"]];
}

- (void)doBrowser { [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:[self htmlPath]]]; }

- (void)doUpdate {
    NSTask *t = [NSTask new];
    t.executableURL = [NSURL fileURLWithPath:@"/usr/bin/python3"];
    t.arguments = @[[self scriptPath]];
    t.currentDirectoryURL = [NSURL fileURLWithPath:SupportDir()];
    t.environment = @{ @"ANIMEBAR_OUT": [SupportDir() stringByAppendingPathComponent:@"anime_board.html"],
                       @"PATH": @"/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin" };
    @try { [t launch]; } @catch (NSException *e) { return; }
    __weak typeof(self) weakSelf = self;
    t.terminationHandler = ^(NSTask *task) {
        dispatch_async(dispatch_get_main_queue(), ^{ [weakSelf load]; });
    };
}


- (void)application:(NSApplication *)app openURLs:(NSArray<NSURL *> *)urls {
    // animebar://anich?title=xxx —— 复制标题并唤起 AniCh
    for (NSURL *u in urls) {
        if (![[u scheme] isEqualToString:@"animebar"]) continue;
        NSString *title = nil;
        for (NSString *pair in [[u query] componentsSeparatedByString:@"&"]) {
            NSRange eq = [pair rangeOfString:@"="];
            if (eq.location == NSNotFound) continue;
            NSString *key = [pair substringToIndex:eq.location];
            if (![key isEqualToString:@"title"]) continue;
            NSString *raw = [pair substringFromIndex:eq.location + 1];
            title = [raw stringByRemovingPercentEncoding];
        }
        if (title.length > 0) {
            NSPasteboard *pb = [NSPasteboard generalPasteboard];
            [pb clearContents];
            [pb setString:title forType:NSPasteboardTypeString];
        }
        [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:@"/Applications/anich.app"]];
    }
}

- (void)doQuit { [NSApp terminate:nil]; }

@end

int main(void) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        AppDelegate *delegate = [AppDelegate new];
        app.delegate = delegate;
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory];
        [app run];
    }
    return 0;
}
