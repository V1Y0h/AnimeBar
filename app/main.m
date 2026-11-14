#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>

static NSString *const kDevDir = @"/Users/jerryli/Documents/deepseek-harness/实验/AnimeBar";

static NSString *SupportDir(void) {
    NSString *p = [@"~/Library/Application Support/AnimeBar" stringByExpandingTildeInPath];
    [[NSFileManager defaultManager] createDirectoryAtPath:p withIntermediateDirectories:YES attributes:nil error:nil];
    return p;
}

static NSString *ResPath(NSString *name) {
    NSString *p = [[[NSBundle mainBundle] resourcePath] stringByAppendingPathComponent:name];
    return [[NSFileManager defaultManager] fileExistsAtPath:p] ? p : nil;
}

// 时间戳前缀的 26 位 ID（Crockford base32，近似 ULID），便于按时间排序
static NSString *NewNoteID(void) {
    static const char *alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
    uint64_t ms = (uint64_t)([[NSDate date] timeIntervalSince1970] * 1000.0);
    char out[27];
    for (int i = 9; i >= 0; i--) { out[i] = alphabet[ms & 31]; ms >>= 5; }
    for (int i = 10; i < 26; i++) { out[i] = alphabet[arc4random_uniform(32)]; }
    out[26] = '\0';
    return [NSString stringWithUTF8String:out];
}

@interface AppDelegate : NSObject <NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate>
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
    [cfg.userContentController addScriptMessageHandler:self name:@"copy"];
    [cfg.userContentController addScriptMessageHandler:self name:@"notesave"];
    self.web = [[WKWebView alloc] initWithFrame:NSMakeRect(0, 0, 1080, 720) configuration:cfg];
    self.web.navigationDelegate = self;
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


- (void)webView:(WKWebView *)webView didFinishNavigation:(WKNavigation *)navigation {
    NSString *path = [SupportDir() stringByAppendingPathComponent:@"notes.json"];
    NSString *json = [NSString stringWithContentsOfFile:path encoding:NSUTF8StringEncoding error:nil];
    if (json.length == 0) return;
    NSString *js = [NSString stringWithFormat:@"window.__initNotes && window.__initNotes(%@)", json];
    [webView evaluateJavaScript:js completionHandler:nil];
}

- (NSString *)htmlPath {
    NSString *s = [SupportDir() stringByAppendingPathComponent:@"anime_board.html"];
    if ([[NSFileManager defaultManager] fileExistsAtPath:s]) return s;
    NSString *b = ResPath(@"anime_board.html");
    if (b) return b;
    return [kDevDir stringByAppendingPathComponent:@"build/anime_board.html"];
}

- (NSString *)scriptPath {
    NSString *s = [SupportDir() stringByAppendingPathComponent:@"anime_board.py"];
    if ([[NSFileManager defaultManager] fileExistsAtPath:s]) return s;
    NSString *b = ResPath(@"anime_board.py");
    if (b) return b;
    return [kDevDir stringByAppendingPathComponent:@"board/anime_board.py"];
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
    if ([msg.name isEqualToString:@"notesave"]) {
        NSString *t = [msg.body isKindOfClass:[NSString class]] ? msg.body : [msg.body description];
        if (t.length) {
            NSString *path = [SupportDir() stringByAppendingPathComponent:@"notes.json"];
            [t writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:nil];
        }
        return;
    }
    if ([msg.name isEqualToString:@"copy"]) {
        NSString *t = [msg.body isKindOfClass:[NSString class]] ? msg.body : [msg.body description];
        if (t.length) {
            NSPasteboard *pb = [NSPasteboard generalPasteboard];
            [pb clearContents];
            [pb setString:t forType:NSPasteboardTypeString];
        }
        return;
    }
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


// 把一行 JSON 原子地追加到 creation-log.jsonl（临时文件 + rename）
- (void)appendJSONLLine:(NSData *)line {
    NSString *path = [SupportDir() stringByAppendingPathComponent:@"creation-log.jsonl"];
    NSMutableData *buf = [NSMutableData new];
    NSData *old = [NSData dataWithContentsOfFile:path];
    if (old.length > 0) {
        [buf appendData:old];
        if (((const char *)old.bytes)[old.length - 1] != '\n') {
            [buf appendBytes:"\n" length:1];
        }
    }
    [buf appendData:line];
    [buf appendBytes:"\n" length:1];

    NSError *err = nil;
    if (![buf writeToFile:path options:NSDataWritingAtomic error:&err]) {
        NSLog(@"capture: 写入失败 %@", err);
        return;
    }
    // 里面有 private 字段，收窄到仅本人可读
    [[NSFileManager defaultManager] setAttributes:@{ NSFilePosixPermissions: @(0600) }
                                     ofItemAtPath:path error:nil];
}

// animebar://capture?t=123.4&src=abema&ep=7&scope=cut&bangumi=423000
- (void)handleCaptureURL:(NSURL *)u {
    NSMutableDictionary *q = [NSMutableDictionary new];
    for (NSString *pair in [[u query] componentsSeparatedByString:@"&"]) {
        NSRange eq = [pair rangeOfString:@"="];
        if (eq.location == NSNotFound) continue;
        NSString *k = [pair substringToIndex:eq.location];
        NSString *v = [[pair substringFromIndex:eq.location + 1] stringByRemovingPercentEncoding];
        if (k.length > 0 && v != nil) q[k] = v;
    }

    NSDateFormatter *iso = [NSDateFormatter new];
    iso.locale = [NSLocale localeWithLocaleIdentifier:@"en_US_POSIX"];
    iso.dateFormat = @"yyyy-MM-dd'T'HH:mm:ssZZZZZ";

    NSMutableDictionary *rec = [NSMutableDictionary new];
    rec[@"schema_version"] = @1;
    rec[@"note_id"] = NewNoteID();
    rec[@"created_at"] = [iso stringFromDate:[NSDate date]];
    rec[@"status"] = @"inbox";                  // inbox = 未复盘
    rec[@"source"] = q[@"src"] ?: @"unknown";
    rec[@"scope"] = q[@"scope"] ?: @"cut";
    if (q[@"ep"] != nil) rec[@"episode"] = @([q[@"ep"] integerValue]);
    if (q[@"t"] != nil) {
        // 取到毫秒，避免 123.40000000000001 这种浮点尾巴
        rec[@"t_start"] = @(round([q[@"t"] doubleValue] * 1000.0) / 1000.0);
    }
    if (q[@"bangumi"] != nil) rec[@"bangumi_id"] = @([q[@"bangumi"] integerValue]);
    rec[@"phenomena"] = @[];
    rec[@"speculations"] = @[];
    rec[@"my_take"] = @"";
    rec[@"evidence"] = @[];

    NSError *err = nil;
    NSData *line = [NSJSONSerialization dataWithJSONObject:rec
                                                  options:NSJSONWritingSortedKeys
                                                    error:&err];
    if (line == nil) {
        NSLog(@"capture: 序列化失败 %@", err);
        return;
    }
    [self appendJSONLLine:line];
}

- (void)application:(NSApplication *)app openURLs:(NSArray<NSURL *> *)urls {
    // animebar://anich?title=xxx —— 复制标题并唤起 AniCh
    for (NSURL *u in urls) {
        if (![[u scheme] isEqualToString:@"animebar"]) continue;
        if ([[u host] isEqualToString:@"capture"]) {   // 捕获记录，不唤起 AniCh
            [self handleCaptureURL:u];
            continue;
        }
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
