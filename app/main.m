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

// 捕获确认浮层：非激活、可加入所有空间、能贴在别人全屏之上
@interface CaptureFlashPanel : NSPanel
@end

@implementation CaptureFlashPanel
- (BOOL)canBecomeKeyWindow { return NO; }
- (BOOL)canBecomeMainWindow { return NO; }
@end

@interface AppDelegate : NSObject <NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate>
@property (strong) NSStatusItem *statusItem;
@property (strong) NSPopover *popover;
@property (strong) WKWebView *web;
@property (strong) CaptureFlashPanel *flashPanel;
@property (strong) NSTextField *flashHead;
@property (strong) NSTextField *flashSub;
@property (assign) NSInteger flashGeneration;
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
    [cfg.userContentController addScriptMessageHandler:self name:@"captures"];
    [cfg.userContentController addScriptMessageHandler:self name:@"triagesave"];
    [cfg.userContentController addScriptMessageHandler:self name:@"capturedelete"];
    [cfg.userContentController addScriptMessageHandler:self name:@"noteadd"];
    [cfg.userContentController addScriptMessageHandler:self name:@"noteupdate"];
    [cfg.userContentController addScriptMessageHandler:self name:@"notedelete"];
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
    if ([msg.name isEqualToString:@"captures"]) {
        // 页面主动来取；回复用 evaluateJavaScript 回调（WKScriptMessageHandler 是单向的）
        NSString *json = [self capturesJSON];
        NSString *js = [NSString stringWithFormat:@"window.__initCaptures && window.__initCaptures(%@)", json];
        [self.web evaluateJavaScript:js completionHandler:nil];
        return;
    }
    if ([msg.name isEqualToString:@"notedelete"]) {
        NSString *t = [msg.body isKindOfClass:[NSString class]] ? msg.body : [msg.body description];
        if (t.length) [self deleteManualNote:t];
        [self.web evaluateJavaScript:@"window.__loadCaptures && window.__loadCaptures()" completionHandler:nil];
        return;
    }
    if ([msg.name isEqualToString:@"noteupdate"]) {
        NSString *t = [msg.body isKindOfClass:[NSString class]] ? msg.body : [msg.body description];
        if (t.length) [self updateManualNote:t];
        [self.web evaluateJavaScript:@"window.__loadCaptures && window.__loadCaptures()" completionHandler:nil];
        return;
    }
    if ([msg.name isEqualToString:@"noteadd"]) {
        [self appendManualNote];
        [self.web evaluateJavaScript:@"window.__initCaptures && window.__loadCaptures()" completionHandler:nil];
        return;
    }
    if ([msg.name isEqualToString:@"capturedelete"]) {
        NSString *t = [msg.body isKindOfClass:[NSString class]] ? msg.body : [msg.body description];
        if (t.length) [self appendCaptureDeleteMac:t];
        return;
    }
    if ([msg.name isEqualToString:@"triagesave"]) {
        NSString *t = [msg.body isKindOfClass:[NSString class]] ? msg.body : [msg.body description];
        if (t.length) [self appendTriageMac:t];
        return;
    }
    if ([msg.name isEqualToString:@"notesave"]) {
        NSString *t = [msg.body isKindOfClass:[NSString class]] ? msg.body : [msg.body description];
        if (t.length) [self writeNotesJSON:t];
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


// 记录条数；不是数组或解析失败都算 0
- (NSUInteger)countOfNotesInData:(NSData *)data {
    if (data.length == 0) return 0;
    id obj = [NSJSONSerialization JSONObjectWithData:data options:0 error:NULL];
    return [obj isKindOfClass:[NSArray class]] ? [(NSArray *)obj count] : 0;
}

// 每次内容变化前留一份快照，只保留最近 5 份
- (void)snapshotNotesData:(NSData *)data {
    if (data.length == 0) return;
    NSString *dir = [SupportDir() stringByAppendingPathComponent:@"notes-backups"];
    [[NSFileManager defaultManager] createDirectoryAtPath:dir
                             withIntermediateDirectories:YES attributes:nil error:nil];
    NSDateFormatter *df = [NSDateFormatter new];
    df.locale = [NSLocale localeWithLocaleIdentifier:@"en_US_POSIX"];
    df.dateFormat = @"yyyyMMdd-HHmmss";
    NSString *name = [NSString stringWithFormat:@"notes-%@.json", [df stringFromDate:[NSDate date]]];
    [data writeToFile:[dir stringByAppendingPathComponent:name]
              options:NSDataWritingAtomic error:nil];

    NSArray *files = [[NSFileManager defaultManager] contentsOfDirectoryAtPath:dir error:nil];
    NSArray *sorted = [files sortedArrayUsingSelector:@selector(compare:)];
    for (NSUInteger i = 0; i + 5 < sorted.count; i++) {
        [[NSFileManager defaultManager] removeItemAtPath:[dir stringByAppendingPathComponent:sorted[i]]
                                                   error:nil];
    }
}

// 落盘前先留快照：内容变了就备份旧内容，条数掉到 0 时额外记一条日志
- (void)writeNotesJSON:(NSString *)text {
    NSString *path = [SupportDir() stringByAppendingPathComponent:@"notes.json"];
    NSData *oldData = [NSData dataWithContentsOfFile:path];
    NSData *newData = [text dataUsingEncoding:NSUTF8StringEncoding];

    BOOL changed = (oldData == nil) || ![oldData isEqualToData:newData];
    NSUInteger oldCount = [self countOfNotesInData:oldData];
    NSUInteger newCount = [self countOfNotesInData:newData];

    if (changed && oldCount > 0) {
        [self snapshotNotesData:oldData];
        if (newCount == 0) {
            NSLog(@"notes: 记录数 %lu → 0，旧内容已存入 notes-backups/",
                  (unsigned long)oldCount);
        }
    }
    [text writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:nil];
}

#pragma mark - 捕获与复盘（与 DSH 端共用数据）

static NSISO8601DateFormatter *IsoFormatter(void) {
    static NSISO8601DateFormatter *f = nil;
    if (f == nil) {
        f = [NSISO8601DateFormatter new];
        f.formatOptions = NSISO8601DateFormatWithInternetDateTime | NSISO8601DateFormatWithFractionalSeconds;
    }
    return f;
}

- (NSArray *)readJSONLLines:(NSString *)path {
    NSData *data = [NSData dataWithContentsOfFile:path];
    if (data.length == 0) return @[];
    NSString *text = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    if (text == nil) return @[];
    NSMutableArray *out = [NSMutableArray array];
    for (NSString *line in [text componentsSeparatedByString:@"\n"]) {
        NSString *trimmed = [line stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
        if (trimmed.length == 0) continue;
        id obj = [NSJSONSerialization JSONObjectWithData:[trimmed dataUsingEncoding:NSUTF8StringEncoding]
                                                options:0 error:NULL];
        if ([obj isKindOfClass:[NSDictionary class]]) [out addObject:obj];
    }
    return out;
}

// 与 DSH 端同一套规则：两个 triage 文件按时间戳后写覆盖（LWW），墓碑表示未复盘
- (NSString *)capturesJSON {
    NSString *dir = SupportDir();
    NSArray *caps = [self readJSONLLines:[dir stringByAppendingPathComponent:@"creation-log.jsonl"]];
    NSArray *tri = [self readJSONLLines:[dir stringByAppendingPathComponent:@"triage.jsonl"]];
    NSArray *triMac = [self readJSONLLines:[dir stringByAppendingPathComponent:@"triage-mac.jsonl"]];
    NSArray *dels = [[self readJSONLLines:[dir stringByAppendingPathComponent:@"capture-deletes.jsonl"]]
                     arrayByAddingObjectsFromArray:
                     [self readJSONLLines:[dir stringByAppendingPathComponent:@"capture-deletes-mac.jsonl"]]];

    NSMutableSet *deleted = [NSMutableSet set];
    for (NSDictionary *row in dels) {
        NSString *nid = row[@"note_id"];
        if ([nid isKindOfClass:[NSString class]]) [deleted addObject:nid];
    }

    NSMutableDictionary *latest = [NSMutableDictionary dictionary];
    for (NSDictionary *row in [tri arrayByAddingObjectsFromArray:triMac]) {
        NSString *nid = row[@"note_id"];
        if (![nid isKindOfClass:[NSString class]]) continue;
        NSString *stamp = row[@"triaged_at"] ?: row[@"cleared_at"];
        double ts = 0;
        if ([stamp isKindOfClass:[NSString class]]) {
            NSDate *d = [IsoFormatter() dateFromString:stamp];
            if (d) ts = d.timeIntervalSince1970;
        }
        NSDictionary *current = latest[nid];
        if (current == nil || ts >= [current[@"ts"] doubleValue]) {
            latest[nid] = @{ @"ts": @(ts), @"row": row };
        }
    }

    NSMutableArray *items = [NSMutableArray array];

    // 手记也进同一个列表：没有时间码，标记为 manual
    NSString *notesPath = [dir stringByAppendingPathComponent:@"notes.json"];
    NSData *notesData = [NSData dataWithContentsOfFile:notesPath];
    if (notesData.length > 0) {
        id parsed = [NSJSONSerialization JSONObjectWithData:notesData options:0 error:NULL];
        if ([parsed isKindOfClass:[NSArray class]]) {
            for (NSDictionary *note in (NSArray *)parsed) {
                if (![note isKindOfClass:[NSDictionary class]]) continue;
                NSMutableDictionary *cap = [@{
                    @"note_id": note[@"id"] ?: NewNoteID(),
                    @"created_at": note[@"createdAt"] ?: @"",
                    @"source": @"manual",
                    @"title": note[@"title"] ?: @"",
                    @"episode": note[@"episode"] ?: [NSNull null],
                } mutableCopy];
                // 手记的正文直接随记录一起返回，不走 triage
                NSMutableDictionary *noteBody = [NSMutableDictionary dictionary];
                for (NSString *k in @[@"phenomena", @"speculations", @"my_take", @"evidence", @"dims", @"title"]) {
                    if (note[k] != nil) noteBody[k] = note[k];
                }
                [items addObject:@{ @"capture": cap, @"triage": [NSNull null], @"note": noteBody }];
            }
        }
    }

    for (NSDictionary *cap in caps) {
        NSString *nid = cap[@"note_id"];
        if (![nid isKindOfClass:[NSString class]]) continue;
        if ([deleted containsObject:nid]) continue;
        NSDictionary *row = latest[nid][@"row"];
        if (row != nil && [row[@"cleared"] boolValue]) row = nil;
        [items addObject:@{ @"capture": cap, @"triage": row ?: [NSNull null] }];
    }

    [items sortUsingComparator:^NSComparisonResult(NSDictionary *a, NSDictionary *b) {
        return [b[@"capture"][@"note_id"] compare:a[@"capture"][@"note_id"]];
    }];

    NSData *json = [NSJSONSerialization dataWithJSONObject:@{ @"items": items }
                                                   options:NSJSONWritingSortedKeys error:NULL];
    return [[NSString alloc] initWithData:json encoding:NSUTF8StringEncoding] ?: @"{\"items\":[]}";
}

// 删除一条手记
- (void)deleteManualNote:(NSString *)noteID {
    NSString *nid = [noteID stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
    if (nid.length == 0) return;
    NSString *path = [SupportDir() stringByAppendingPathComponent:@"notes.json"];
    NSData *data = [NSData dataWithContentsOfFile:path];
    if (data.length == 0) return;
    id parsed = [NSJSONSerialization JSONObjectWithData:data options:0 error:NULL];
    if (![parsed isKindOfClass:[NSArray class]]) return;
    NSMutableArray *kept = [NSMutableArray array];
    for (NSDictionary *row in (NSArray *)parsed) {
        if ([row isKindOfClass:[NSDictionary class]] && [nid isEqual:row[@"id"]]) continue;
        [kept addObject:row];
    }
    NSData *json = [NSJSONSerialization dataWithJSONObject:kept options:NSJSONWritingSortedKeys error:NULL];
    [json writeToFile:path options:NSDataWritingAtomic error:NULL];
}

// 更新一条手记（保持 notes.json 原有格式：标签仍是中文）
- (void)updateManualNote:(NSString *)text {
    id obj = [NSJSONSerialization JSONObjectWithData:[text dataUsingEncoding:NSUTF8StringEncoding]
                                            options:0 error:NULL];
    if (![obj isKindOfClass:[NSDictionary class]]) return;
    NSString *nid = obj[@"id"];
    if (![nid isKindOfClass:[NSString class]]) return;

    NSString *path = [SupportDir() stringByAppendingPathComponent:@"notes.json"];
    NSMutableArray *notes = [NSMutableArray array];
    NSData *data = [NSData dataWithContentsOfFile:path];
    if (data.length > 0) {
        id parsed = [NSJSONSerialization JSONObjectWithData:data options:0 error:NULL];
        if ([parsed isKindOfClass:[NSArray class]]) notes = [parsed mutableCopy];
    }

    for (NSUInteger i = 0; i < notes.count; i++) {
        NSDictionary *row = notes[i];
        if (![row isKindOfClass:[NSDictionary class]]) continue;
        if (![nid isEqual:row[@"id"]]) continue;
        NSMutableDictionary *updated = [row mutableCopy];
        for (NSString *k in @[@"title", @"phenomena", @"speculations", @"my_take", @"evidence", @"dims"]) {
            if (obj[k] != nil) updated[k] = obj[k];
        }
        notes[i] = updated;
        break;
    }

    NSData *json = [NSJSONSerialization dataWithJSONObject:notes options:NSJSONWritingSortedKeys error:NULL];
    [json writeToFile:path options:NSDataWritingAtomic error:NULL];
}

// 新建一条手记（空壳），落 notes.json
- (void)appendManualNote {
    NSString *path = [SupportDir() stringByAppendingPathComponent:@"notes.json"];
    NSMutableArray *notes = [NSMutableArray array];
    NSData *data = [NSData dataWithContentsOfFile:path];
    if (data.length > 0) {
        id parsed = [NSJSONSerialization JSONObjectWithData:data options:0 error:NULL];
        if ([parsed isKindOfClass:[NSArray class]]) notes = [parsed mutableCopy];
    }
    [notes insertObject:@{
        @"id": NewNoteID(),
        @"title": @"",
        @"episode": @"",
        @"phenomena": @[],
        @"speculations": @[],
        @"my_take": @"",
        @"evidence": @"",
        @"dims": @{},
        @"createdAt": [IsoFormatter() stringFromDate:[NSDate date]],
    } atIndex:0];
    NSData *json = [NSJSONSerialization dataWithJSONObject:notes options:NSJSONWritingSortedKeys error:NULL];
    [json writeToFile:path options:NSDataWritingAtomic error:NULL];
}

// Mac 侧删除捕获：写自己的墓碑文件，DSH 那边一并读取
- (void)appendCaptureDeleteMac:(NSString *)noteID {
    NSString *id = [noteID stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
    if (id.length == 0) return;
    NSDictionary *record = @{ @"note_id": id,
                              @"deleted_at": [IsoFormatter() stringFromDate:[NSDate date]] };
    NSData *line = [NSJSONSerialization dataWithJSONObject:record options:NSJSONWritingSortedKeys error:NULL];
    NSString *path = [SupportDir() stringByAppendingPathComponent:@"capture-deletes-mac.jsonl"];
    NSMutableData *buf = [NSMutableData new];
    NSData *old = [NSData dataWithContentsOfFile:path];
    if (old.length > 0) {
        [buf appendData:old];
        if (((const char *)old.bytes)[old.length - 1] != '\n') [buf appendBytes:"\n" length:1];
    }
    [buf appendData:line];
    [buf appendBytes:"\n" length:1];
    [buf writeToFile:path options:NSDataWritingAtomic error:NULL];
}

// Mac 侧复盘写入自己的文件，DSH 那边按时间戳合并
- (void)appendTriageMac:(NSString *)text {
    NSData *incoming = [text dataUsingEncoding:NSUTF8StringEncoding];
    id obj = [NSJSONSerialization JSONObjectWithData:incoming options:0 error:NULL];
    if (![obj isKindOfClass:[NSDictionary class]]) return;

    NSMutableDictionary *record = [obj mutableCopy];
    record[@"schema_version"] = @1;
    if ([record[@"clear"] boolValue]) {
        // 清空复盘：追加墓碑，读取时后者覆盖前者
        record[@"cleared"] = @YES;
        record[@"cleared_at"] = [IsoFormatter() stringFromDate:[NSDate date]];
        [record removeObjectForKey:@"clear"];
        [record removeObjectForKey:@"phenomena"];
        [record removeObjectForKey:@"speculations"];
        [record removeObjectForKey:@"my_take"];
    } else {
        record[@"triaged_at"] = [IsoFormatter() stringFromDate:[NSDate date]];
    }

    NSData *line = [NSJSONSerialization dataWithJSONObject:record options:NSJSONWritingSortedKeys error:NULL];
    NSString *path = [SupportDir() stringByAppendingPathComponent:@"triage-mac.jsonl"];
    NSMutableData *buf = [NSMutableData new];
    NSData *old = [NSData dataWithContentsOfFile:path];
    if (old.length > 0) {
        [buf appendData:old];
        if (((const char *)old.bytes)[old.length - 1] != '\n') [buf appendBytes:"\n" length:1];
    }
    [buf appendData:line];
    [buf appendBytes:"\n" length:1];
    [buf writeToFile:path options:NSDataWritingAtomic error:NULL];
    [[NSFileManager defaultManager] setAttributes:@{ NSFilePosixPermissions: @(0600) }
                                     ofItemAtPath:path error:nil];
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

// 捕获后浮 2.5 秒，让你确认「记下了」。
// 关键：orderFrontRegardless 而不是 makeKeyAndOrderFront——不能把播放器的焦点抢走。
- (void)flashCaptureAt:(double)t title:(NSString *)title {
    if (self.flashPanel == nil) {
        NSRect r = NSMakeRect(0, 0, 300, 88);
        CaptureFlashPanel *p = [[CaptureFlashPanel alloc]
            initWithContentRect:r
                      styleMask:(NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel)
                        backing:NSBackingStoreBuffered
                          defer:NO];
        p.collectionBehavior = NSWindowCollectionBehaviorCanJoinAllSpaces
                             | NSWindowCollectionBehaviorFullScreenAuxiliary
                             | NSWindowCollectionBehaviorStationary;
        p.level = NSStatusWindowLevel;
        p.hidesOnDeactivate = NO;
        p.opaque = NO;
        p.backgroundColor = [NSColor clearColor];

        NSVisualEffectView *bg = [[NSVisualEffectView alloc] initWithFrame:r];
        bg.material = NSVisualEffectMaterialHUDWindow;
        bg.blendingMode = NSVisualEffectBlendingModeBehindWindow;
        bg.state = NSVisualEffectStateActive;
        bg.wantsLayer = YES;
        bg.layer.cornerRadius = 14;
        bg.layer.masksToBounds = YES;

        self.flashHead = [NSTextField labelWithString:@""];
        self.flashHead.font = [NSFont monospacedSystemFontOfSize:15 weight:NSFontWeightMedium];
        self.flashHead.textColor = [NSColor labelColor];
        self.flashHead.frame = NSMakeRect(18, 48, 264, 22);
        self.flashHead.lineBreakMode = NSLineBreakByTruncatingTail;

        self.flashSub = [NSTextField labelWithString:@""];
        self.flashSub.font = [NSFont systemFontOfSize:11];
        self.flashSub.textColor = [NSColor secondaryLabelColor];
        self.flashSub.frame = NSMakeRect(18, 24, 264, 18);
        self.flashSub.lineBreakMode = NSLineBreakByTruncatingTail;

        [bg addSubview:self.flashHead];
        [bg addSubview:self.flashSub];
        p.contentView = bg;
        self.flashPanel = p;
    }

    int total = (int)(t + 0.5);
    self.flashHead.stringValue = [NSString stringWithFormat:@"已记录  %02d:%02d", total / 60, total % 60];
    self.flashSub.stringValue = (title.length > 0) ? title : @"（无片名）";

    NSScreen *scr = [NSScreen mainScreen] ?: [NSScreen screens].firstObject;
    NSRect vf = scr.visibleFrame;
    NSRect f = self.flashPanel.frame;
    f.origin.x = NSMaxX(vf) - f.size.width - 24;
    f.origin.y = NSMaxY(vf) - f.size.height - 24;
    [self.flashPanel setFrame:f display:NO];
    [self.flashPanel orderFrontRegardless];

    self.flashGeneration += 1;
    NSInteger gen = self.flashGeneration;
    __weak typeof(self) weakSelf = self;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(2.5 * NSEC_PER_SEC)),
                   dispatch_get_main_queue(), ^{
        if (gen != weakSelf.flashGeneration) return;
        [weakSelf.flashPanel orderOut:nil];
    });
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
    // 播放器给的片名，Triage 时用来认片
    NSString *titleParam = (NSString *)q[@"title"];
    if (titleParam.length > 0) rec[@"title"] = titleParam;
    rec[@"scope"] = q[@"scope"] ?: @"cut";
    if (q[@"ep"] != nil) rec[@"episode"] = @([q[@"ep"] integerValue]);
    if (q[@"t"] != nil) {
        // 取到毫秒，避免 123.40000000000001 这种浮点尾巴
        // 用 NSDecimalNumber 而不是 double：后者会被 JSON 序列化成
        // 3.7919999999999998 这种尾巴，直接写进数据文件很难看
        rec[@"t_start"] = [NSDecimalNumber decimalNumberWithString:
            [NSString stringWithFormat:@"%.3f", [q[@"t"] doubleValue]]];
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
    [self flashCaptureAt:(double)[rec[@"t_start"] doubleValue] title:(NSString *)rec[@"title"]];
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
