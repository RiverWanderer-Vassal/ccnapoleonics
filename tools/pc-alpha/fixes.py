import sys; sys.path.insert(0,'/home/claude/tools'); from modpatch import *
FIXES=[]
def fix(fn): FIXES.append(fn); return fn

@fix
def f01_sendto_board(b):
    """Grid-location Send To traits had no board name, so VASSAL never moved the piece:
    the P&C hex grid was never laid (Setup Board), units never walked their path (Move Action),
    and Target Controls could not re-attach to its target."""
    def setb(proto, startswith, board):
        def fn(T,S):
            i=idx(T,startswith); T[i]=set_field(T[i],4,board); return T,S
        b.edit_proto(proto,fn,f'Send To board name set to {board}')
    setb('Setup Board','sendto;;57892,0,nextRow','{CurrentBoard.replace("Side Board","Inland")}')
    setb('Move Action','sendto;;57913,0,moveStep','$CurrentBoard$')
    setb('Target Controls','sendto;','$CurrentBoard$')

@fix
def f02_clear_stale_paths(b):
    """While plotting a move map, neighbouring hexes the unit may not enter (e.g. a friendly unit's hex)
    still received a path value but were never shown, and the reset only cleared shown hexes.
    The stale path made the next click on that hex try to 'move' there, so the unit in it could not be ordered."""
    newgkc='globalkey;;57839,0,reset;57848,0,hideStep;{path != ""};false;1;false;false;;Clear stale paths left on hexes outside the shown move map;0;COUNTER|true|ZONE|$cMain$||$cBoard$||0|0||true|BasicName|Hex Controller|EQUALS||;false;path:,maxMove:0'
    for proto in ('Movement Widget-Unit','Movement Widget-Leader','Breakthrough Widget'):
        def fn(T,S):
            i=idx(T,'globalkey;;57839,0,reset;57848,0,hideStep;;'); T.insert(i+1,newgkc); S.insert(i+1,''); return T,S
        b.edit_proto(proto,fn,'reset also clears stale path on every hex controller')

@fix
def f03_set_stopped(b):
    """Point & Click moves set MarkerLevel but never the unit's 'stopped' flag, which Drag & Drop sets when terrain
    stops the move (forest, town, etc.). Take Ground and the Cavalry Forward card read 'stopped', so a P&C unit
    that ended its move in stopping terrain could illegally take ground / be offered Cavalry Forward
    (and a unit stopped on an earlier turn stayed flagged). Now set from the destination icon, as Take Ground already does."""
    old=',path:$path$'
    new=',stopped:{$mp_LDR$ == LDR ? ($icon$ == 1 || $icon$ == 2) \\: stopped},path:$path$'
    for proto in ('Movement Widget-Base','Breakthrough Widget-Base'):
        def fn(T,S):
            i=idx(T,'globalkey;;57875,0,gkcMovePieces;57876,0,movePath;')
            assert T[i].endswith(old), T[i][-80:]
            T[i]=T[i][:-len(old)]+new; return T,S
        b.edit_proto(proto,fn,'gkcMovePieces also sets stopped from destination icon')

@fix
def f04_order_unit_with_leader(b):
    """Clicking a hex holding a unit with an attached leader sent the order click to the leader
    (filter LDR == CountLocation("LDR")), and a leader stacked with a unit can't be ordered on his own,
    so nothing happened: the unit could never be ordered in Point & Click. The click now goes to the unit
    when one is present, and to the leader only when he is alone (a Garrison still gets it as before)."""
    old='{LDR == CountLocation("LDR")}'
    new='{LDR == (CountLocation("{Type == \\"Unit\\"}") > 0 ? 0 : CountLocation("LDR"))}'
    def fn(T,S):
        i=idx(T,'globalkey;;57835,0,gkcClick;57759,0,clickBlock;')
        assert old in T[i]; T[i]=T[i].replace(old,new,1); return T,S
    b.edit_proto('Hex Control',fn,'order click goes to the unit when a leader is attached')

@fix
def f05_spend_allowance(b):
    """After a Point & Click move the unit kept its full movement allowance, so clicking it again showed a fresh
    move map from the new hex and it could move a second full move (e.g. foot artillery under Bombard: 3 + 3 hexes).
    Drag & Drop counts the whole path against the allowance. The moved unit's maxMove is now set to 0, so a re-click
    shows only its own hex (Undo still corrects a mis-click). Cards that add movement afterwards (Cavalry Forward:
    maxMove + 1) then give exactly the extra hex."""
    old=',path:$path$'
    new=',maxMove:{$mp_LDR$ == LDR ? 0 \\: maxMove},path:$path$'
    for proto in ('Movement Widget-Base','Breakthrough Widget-Base'):
        def fn(T,S):
            i=idx(T,'globalkey;;57875,0,gkcMovePieces;57876,0,movePath;')
            assert T[i].endswith(old); T[i]=T[i][:-len(old)]+new; return T,S
        b.edit_proto(proto,fn,'gkcMovePieces spends the movement allowance (maxMove 0)')

@fix
def f06_clean_slate_after_undo(b):
    """The move-map shading (Area of Effect 'path', not global) is local-only, so VASSAL Undo cannot switch it off:
    after Undo of a shown map (or of a move) every hex of that map stayed 'path_Active'. The next map then skipped
    those hexes (nextStep requires !path_Active) and clicks on them did nothing. Each new move map now starts by
    clearing any hex still shaded or holding a path, and the reset also clears shaded hexes, not just stale paths."""
    oldf='globalkey;;57839,0,reset;57848,0,hideStep;{path != ""};'
    newf='globalkey;;57839,0,reset;57848,0,hideStep;{path != "" || path_Active};'
    init=('globalkey;;57553,0,initMarker;57848,0,hideStep;{path != "" || path_Active};false;1;false;false;;'
          'Start each move map from a clean slate (shading is local, so Undo can leave it on);0;'
          'COUNTER|true|ZONE|$cMain$||$cBoard$||0|0||true|BasicName|Hex Controller|EQUALS||;false;path:,maxMove:0')
    for proto in ('Movement Widget-Unit','Movement Widget-Leader','Breakthrough Widget'):
        def fn(T,S):
            i=idx(T,oldf); T[i]=T[i].replace(oldf,newf,1); T.insert(0,init); S.insert(0,''); return T,S
        b.edit_proto(proto,fn,'new map clears leftover shading/paths; reset clears shaded hexes too')

@fix
def f07_click_ignores_unshown_paths(b):
    """A hex whose path is not part of the move map on show (left by Undo, or never shaded) still made a click count
    as 'move here' (clickCase 3), which is hidden on unshaded hexes, so the click did nothing - e.g. ordering another
    unit right after undoing a move. A click now only counts as a move when the hex is actually shaded."""
    old='{path == "" ? (CountLocation("{ordered}") == 0 ? 1 \\: 2)'
    new='{path == "" || !path_Active ? (CountLocation("{ordered}") == 0 ? 1 \\: 2)'
    def fn(T,S):
        i=idx(T,'PROP;clickCase;'); assert old in T[i], T[i]; T[i]=T[i].replace(old,new,1); return T,S
    b.edit_proto('Hex Control',fn,'clickCase treats unshaded paths as no path')

@fix
def f08_bar_drags_in_movement(b):
    """With Point & Click selected, a unit dragged during the Movement phase was not checked at all (rawMoveCase 9):
    once a unit had moved by click its hex is unmasked, so it could be dragged on any distance through any terrain
    with no marker. Drags were only barred in the Orders phase. They are now also sent back in the Movement phase,
    except the click-move's own steps (the hex is on the unit's plotted path). As in the Orders phase this includes
    leaders, so a dragged unit + leader stack goes back together."""
    old='{LocationName != origLoc && gMoveClick && gPhase == ORDER}'
    new='{LocationName != origLoc && gMoveClick && (gPhase == ORDER || (gPhase == MOVEMENT && !(path != "" && path.contains(LocationName))))}'
    def fn(T,S):
        i=idx(T,'macro;Reject movement in Orders phase'); assert old in T[i]; T[i]=T[i].replace(old,new,1); return T,S
    b.edit_proto('Move Action',fn,'drags also sent back in the Movement phase (P&C)')
    b.replace_raw('Drag &amp; Drop is barred during Orders phase. ','Drag &amp; Drop is barred during the Orders and Movement phases. ','mMoveBarred text covers Movement phase')

@fix
def f09_keep_move_mode_on_load(b):
    """Every session launch (loading a saved game, joining) runs ghkInitialise, which set gMoveDrag back to true.
    A Point & Click game reloaded from a save therefore ran Drag & Drop movement checks on every click move as well
    (the Take Ground control switches gMoveDrag off for exactly this reason), so moves could be marked No Entry.
    gMoveDrag is now only defaulted to true before the game has started; afterwards it follows the chosen rules."""
    old='desc="Sets up the game startup preference" disabledIcon="" hideWhenDisabled="false" hotkey="57356,0,ghkInitialise" icon="" propChanger="P,true"'
    new='desc="Sets up the game startup preference" disabledIcon="" hideWhenDisabled="false" hotkey="57356,0,ghkInitialise" icon="" propChanger="P,{!gGameStarted || gMoveRules.startsWith(&quot;Drag&quot;)}"'
    b.replace_raw(old,new,'gMoveDrag re-initialised from gMoveRules once the game has started')

@fix
def f10_show_moves_for_unit_not_leader(b):
    """When a card auto-orders both a unit and its attached leader (e.g. Assault Left Flank), clicking the hex sent
    'move' to both: the unit placed its move map, then the leader's widget replaced it and withdrew (stacked leader),
    so no map appeared for either. The show-moves click now goes only to the unit when one is present, and to the
    leader only when he is alone (same rule as the order click, fix 4)."""
    old='globalkey;;57836,0,gkcShowMove;57834,0,move;;'
    new='globalkey;;57836,0,gkcShowMove;57834,0,move;{Type == "Unit" || CountLocation("{Type == \\"Unit\\"}") == 0};'
    def fn(T,S):
        i=idx(T,old); T[i]=T[i].replace(old,new,1); return T,S
    b.edit_proto('Hex Control',fn,'show-moves click goes to the unit, not its attached leader')

@fix
def f11_move_leader_alone(b):
    """A leader attached to an ordered unit could not move on his own in Point & Click: every click on the hex
    (order, show moves, move) goes to the unit, and drags are barred. The right-click 'Select Leader Move' command
    of the older hex control had been dropped, leaving only its hide rule. It is back as 'Move Leader' on the hex
    (shown when an ordered unit has a leader stacked with it): it shows the leader's own move map, and the leader
    then moves alone, taking an order exactly as dragging him away does in Drag & Drop."""
    hide_old='hideCmd;Leader stacked, not on Garrison;Hide;'
    hide_new=('hideCmd;Move Leader only in Orders/Movement with an ordered unit, the leader not yet moved away, and an order left if he is not yet ordered;Hide;'
              '{!gMoveClick || gPhase !~ ORDERregex || CountLocation("{Type == \\"Unit\\" && ordered}") == 0 '
              '|| CountLocation("{LDR == 1 && LocationName == origLoc}") == 0 || (gOrders <= 0 && CountLocation("{LDR == 1 && !ordered}") > 0)};57877\\,0\\,gkcMoveLeader')
    tgt_here='COUNTER|true|CURLOC|||||0|0||true|LDR|1|EQUALS||'
    add=[
     'macro;Move the attached leader on his own;Move Leader;57877,0,gkcMoveLeader;;;57897\\,0\\,ldrClearPrev,57893\\,0\\,ldrOrder,57898\\,0\\,ldrMaxMove,57899\\,0\\,ldrShowMove;false;;;counted;;;;false;;1;1',
     'globalkey;;57897,0,ldrClearPrev;86,195;;false;1;false;true;;Remove the move map on show (same hex: the leader widget would otherwise remove itself);-1;'
       'COUNTER|true|LOCATION|$cMain$|||$gMoveOrig$|0|0||true|mp_AttachCount|0|GREATER||;false;',
     'globalkey;;57893,0,ldrOrder;79,130;{!ordered};false;1;false;true;;An unordered leader is ordered first (his own Order Leader command: takes an order and detaches him, as a drag away does);-1;'+tgt_here+';false;',
     'globalkey;;57898,0,ldrMaxMove;57800,0,setMaxMove;{maxMove == ""};false;1;false;true;;Leader not yet ordered has no move allowance until set;-1;'+tgt_here+';false;',
     'globalkey;;57899,0,ldrShowMove;57834,0,move;;false;1;false;true;;Show the move map for the attached leader only (he then moves alone);-1;'+tgt_here+';false;',
    ]
    def fn(T,S):
        i=idx(T,hide_old)
        for t in reversed(add): T.insert(i+1,t); S.insert(i+1,'')
        T.insert(i,hide_new); S.insert(i,''); return T,S
    b.edit_proto('Hex Control',fn,'Move Leader command restored on the hex')

@fix
def f12_take_ground_uses_move_path(b):
    """Take Ground and CFR moved the unit (and its attached leader) by sending Move Action's moveStep key directly.
    moveStep's Send To reads the hex from path.substring(loc, loc + 3), where loc is the index of the movePath loop.
    VASSAL keeps that index after the loop, so a unit or leader that had earlier made a click move of 2+ hexes had
    loc = 3 or more: the substring failed ('Expression evaluation error', then 'Grid location not found') and the piece
    stayed put. They now send movePath, which runs the same Send To once with loc reset to 0."""
    for proto in ('Hex Control Take Ground','Hex Control CFR Destination'):
        def fn(T,S):
            n=0
            for i,t in enumerate(T):
                for k in (';57856,0,moveStep;',';57851,0,moveStep;'):
                    if t.startswith('globalkey;') and k in t: T[i]=t.replace(k,';57933,0,movePath;',1); n+=1
            assert n==2, (proto,n); return T,S
        b.edit_proto(proto,fn,'unit and leader moved with movePath (loop index reset), not moveStep')

@fix
def f13_leader_map_from_his_hex(b):
    """The leader's move map attached the hexes it may use with the rule 'not a hex holding a leader', and the exception
    meant to let in his own hex compared UniqueID (never equal for a hex) instead of LocationName as the unit map does.
    So the map never started from the leader's hex: it grew from whichever neighbouring hex VASSAL happened to seed
    (it varied between runs), paths missed the first step and the reach was off by a hex. The leader's own hex is now
    included, as for units."""
    old='{UniqueID == "$UniqueID$" || (maxMove != 9'
    new='{LocationName == "$LocationName$" || (maxMove != 9'
    def fn(T,S):
        i=idx(T,'attach;fullgrid;'); assert old in T[i]; T[i]=T[i].replace(old,new,1); return T,S
    b.edit_proto('Movement Widget-Leader',fn,'leader map includes his own hex (LocationName, not UniqueID)')

@fix
def f14_move_unit_before_leader(b):
    """A click move sent movePath to the unit and its attached leader in one Global Key Command, and VASSAL does not
    fix the order in which it reaches them. When the leader happened to go first, he stepped away from his unit
    and his own move checks treated it as a separate leader move: he was marked ordered and took an extra order
    ('Orders limit exceeded'), and cards that order only certain units (Bayonet Charge, Force March: infantry only)
    raised their alert for him. Whether it happened varied from one move to the next. The command is now split in
    two: the unit moves first, then the leader joins it, as when the stack is dragged. Take Ground and CFR, which
    sent the leader first, now also send the unit first."""
    for proto in ('Movement Widget-Base','Breakthrough Widget-Base'):
        def fn(T,S):
            i=idx(T,'globalkey;;57875,0,gkcMovePieces;57876,0,movePath;;')
            t=T[i]; head='globalkey;;57875,0,gkcMovePieces;57876,0,movePath;'
            unit=t.replace(head+';',head+'{LDR != 1};',1); ldr=t.replace(head+';',head+'{LDR == 1};',1)
            assert unit!=t and ldr!=t
            T[i]=ldr; T.insert(i,unit); S.insert(i,''); return T,S
        b.edit_proto(proto,fn,'move the unit first, then the attached leader (was in arbitrary order)')
    for proto in ('Hex Control Take Ground','Hex Control CFR Destination'):
        def fn2(T,S):
            li=[i for i,t in enumerate(T) if t.startswith('globalkey;') and ';57933,0,movePath;' in t and 'Send for the (stacked) leader' in t]
            ui=[i for i,t in enumerate(T) if t.startswith('globalkey;') and ';57933,0,movePath;' in t and 'Send for the unit' in t]
            assert len(li)==1 and len(ui)==1, (proto,li,ui)
            l,u=li[0],ui[0]
            if l<u: T[l],T[u]=T[u],T[l]; S[l],S[u]=S[u],S[l]
            return T,S
        b.edit_proto(proto,fn2,'unit sent before its attached leader')

@fix
def f15_squares_and_unorder(b):
    """Point & Click had no way to unorder, and no way to take a unit out of square: the hex control covers the
    army pieces, so their own right-click Order (toggle) and UnSquare commands can't be reached, and the hex's
    Order command is hidden once the unit is ordered. A unit in square also got a move map, although a square
    may not move (rules; it may be ordered to battle).
    - Hex right-click 'Unorder': clears any move map on show and sends the unit's (then the leader's) own Order
      toggle to every ordered piece in the hex that has not moved, giving the orders back as in Drag & Drop.
    - Hex right-click 'UnSquare': for an ordered unit in square. It starts the Movement phase (as showing a move map
      does, because the unit's UnSquare works only in the Movement phase) and sends the unit's own UnSquare,
      which keeps its rule: not while enemy cavalry is adjacent (the hex command is then not offered).
    - A unit in square no longer gets a move map when its hex is clicked."""
    old_show='{Type == "Unit" || CountLocation("{Type == \\"Unit\\"}") == 0}'
    new_show='{(Type == "Unit" && !(SqMarker =~ "[1-9]")) || CountLocation("{Type == \\"Unit\\"}") == 0}'
    here='COUNTER|true|CURLOC|||||0|0||false|||EQUALS||'
    unmoved='ordered && LocationName == origLoc && Side == gCombatLead'
    add=[
     'hideCmd;Unorder in P&C: something ordered here that has not moved;Hide;{!gMoveClick || gPhase !~ ORDERregex || CountLocation("{'+unmoved.replace('"','\\"')+'}") == 0};57945\\,0\\,hexUnorder',
     'hideCmd;UnSquare in P&C: an ordered unit in square here;Hide;{!gMoveClick || gPhase !~ ORDERregex || CountLocation("{ordered && SqMarker =~ \\"[1-9]\\" && Side == gCombatLead}") == 0 || CountRange(1,1,"CAV","{inBattle && Side == gCombatTarget}") > 0};57950\\,0\\,hexUnsquare',
     'macro;Give back the orders of unmoved pieces here (P&C proxy for their Order toggle);Unorder;57945,0,hexUnorder;;;57897\\,0\\,ldrClearPrev,57960\\,0\\,hexUnordUnit,57967\\,0\\,hexUnordLdr;false;;;counted;;;;false;;1;1',
     'globalkey;;57960,0,hexUnordUnit;79,130;{Type == "Unit" && '+unmoved+'};false;1;false;true;;Unit Order toggle;-1;'+here+';false;',
     'globalkey;;57967,0,hexUnordLdr;79,130;{LDR == 1 && '+unmoved+'};false;1;false;true;;Leader Order toggle;-1;'+here+';false;',
     'macro;Take the unit here out of square (P&C proxy for its UnSquare);UnSquare;57950,0,hexUnsquare;;;57897\\,0\\,ldrClearPrev,57979\\,0\\,hexSqPhase,57983\\,0\\,hexSqOut;false;;;counted;;;;false;;1;1',
     'setprop;gPhaseLock;false,0,100,false;:57979\\,0\\,hexSqPhase:P\\,$MOVEMENT$;UnSquare happens in the Movement phase;Current Zone/Current Map/Module;',
     'setprop;gPhase;false,0,100,false;:57979\\,0\\,hexSqPhase:P\\,$MOVEMENT$;UnSquare happens in the Movement phase;Current Zone/Current Map/Module;',
     'globalkey;;57983,0,hexSqOut;85,130;{SqMarker =~ "[1-9]" && ordered && Side == gCombatLead};false;1;false;true;;Unit UnSquare;-1;'+here+';false;',
    ]
    def fn(T,S):
        i=idx(T,'globalkey;;57836,0,gkcShowMove;57834,0,move;'); assert old_show in T[i], T[i][:200]
        T[i]=T[i].replace(old_show,new_show,1)
        j=idx(T,'hideCmd;Leader stacked, not on Garrison;Hide;')
        for t in reversed(add): T.insert(j,t); S.insert(j,'')
        return T,S
    b.edit_proto('Hex Control',fn,'Unorder and UnSquare on the hex; no move map for a square')

@fix
def f16_report_issue_diagnostics(b):
    """Help > Report an Issue opened a plain GitHub issue with only the module/VASSAL versions and scenario, and added
    alpha/beta to the assignees instead of the labels. It now opens the repository's structured bug form
    (.github/ISSUE_TEMPLATE/bug_report.yml) with the environment and game state filled in (#536)."""
    E='java.net.URLEncoder.encode'
    def q(name, expr): return '"&'+name+'=" + '+E+'('+expr+', "UTF-8")'
    env=('"Module " + ModuleVersion + "\\n" + "VASSAL " + VassalVersionRunning + "\\n" + '
         '"Java " + java.lang.System.getProperty("java.version") + " (" + java.lang.System.getProperty("java.vendor") + ")\\n" + '
         '"OS " + java.lang.System.getProperty("os.name") + " " + java.lang.System.getProperty("os.version") + " " + java.lang.System.getProperty("os.arch") + "\\n" + '
         '"Max heap " + (java.lang.Runtime.getRuntime().maxMemory() / 1048576) + " MB"')
    scen=('(buildMode ? "build mode" : scenarioName + " (" + codex + ") https://www.commandsandcolors.net/napoleonics/maps/" + '
          '(codex.equals("") ? "" : (codex.length() < 3 ? "0".repeat(3 - codex.length()) : "") + codex + ".html"))')
    phase='(gPhase == COMMAND ? "Command" : gPhase == ORDER ? "Order" : gPhase == MOVEMENT ? "Movement" : gPhase == COMBAT ? "Combat" : gPhase == DRAW ? "Draw" : "other") + " (" + gPhase + ")"'
    state=('"Game started: " + gGameStarted + "\\n" + "Turn: " + gTurn + "\\n" + "Phase: " + '+phase+' + "\\n" + '
           '"Active side: " + gActiveSide + "\\n" + "Combat lead: " + gCombatLead + "\\n" + '
           '"Card in play: " + activeCard + "\\n" + "Order scope: " + gCmdScope + "\\n" + "Orders left: " + gOrders + "\\n" + '
           '"Movement rules: " + gMoveRules + "\\n" + "Player side: " + PlayerSide + "\\n" + '
           '"Solitaire: " + isSolitaire + "\\n" + "Offline: " + isOffline + "\\n" + "Dice widget: " + gDiceControl')
    label='(ModuleVersion =~ ".*[bB]eta.*" ? "bug,beta" : ModuleVersion =~ ".*[0-9-]a[0-9].*" ? "bug,alpha" : "bug")'
    expr=('{"https://github.com/RiverWanderer-Vassal/ccnapoleonics/issues/new?template=bug_report.yml" + '
          +q('labels',label)+' + '+q('title','"[" + ModuleVersion + "] "')+' + '
          +q('version',env)+' + '+q('scenario',scen)+' + '+q('state',state)+'}')
    import re as _re
    from xml.sax.saxutils import quoteattr
    m=_re.search(r'<VASSAL\.build\.module\.documentation\.BrowserHelpFile startingPage="([^"]*)" title="Report an Issue[^"]*"/>', b.raw)
    assert m, 'Report an Issue link not found'
    newattr=expr.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    b.raw=b.raw[:m.start(1)]+newattr+b.raw[m.end(1):]
    b.log.append('Report an Issue: opens the bug form with diagnostics (#536)')

CHANGELOG=[
 ('005','505 P&amp;C: grid-location Send To traits given a board name - move grid is laid and units move (also fixes Take Ground, CFR and Breakthrough moves in D&amp;D)'),
 ('005','506 P&amp;C: move-map reset clears stale paths on all hex controllers (unit next to a moving unit could not be ordered)'),
 ('005','507 P&amp;C: click move sets the unit stopped flag from the terrain (Take Ground / Cavalry Forward)'),
 ('005','508 P&amp;C: hex click orders the unit, not the attached leader'),
 ('005','509 P&amp;C: click move spends the movement allowance (no second full move)'),
 ('005','510 P&amp;C: each move map starts clean - Undo no longer leaves a broken map'),
 ('005','511 P&amp;C: clicking a hex with an unshaded path orders/shows instead of doing nothing'),
 ('005','512 P&amp;C: drags also sent back in the Movement phase (unchecked moves); message updated'),
 ('005','513 P&amp;C: reloading a saved game no longer switches Drag &amp; Drop movement checks back on'),
 ('005','514 P&amp;C: unit with attached leader both ordered by a card (e.g. Assault) now shows its move map'),
 ('005','515 P&amp;C: right-click Move Leader on the hex moves an attached leader on his own'),
 ('005','516 Take Ground / CFR: unit or leader that had click-moved 2+ hexes failed to move (moveStep loop index)'),
 ('005','517 P&amp;C: leader move map starts from the leader hex (was seeded from a random neighbour)'),
 ('005','518 P&amp;C: unit moves before its attached leader - no stray leader order, no Bayonet Charge / Force March alerts'),
 ('005','519 P&amp;C: hex right-click Unorder and UnSquare; a unit in square gets no move map'),
 ('005','536 Report an Issue opens the GitHub bug form with module, Java, scenario and game-state details; labels fixed'),
]
VERSION='5.1.0-a19.081'
def apply(upto=None, out='bf_work.xml', vmod='work.vmod', release=False):
    b=Build('/home/claude/vmod/x/buildFile.xml')
    for f in FIXES[:upto]: f(b)
    if release:
        anchor='<VASSAL.build.module.folder.ModuleSubFolder desc="496 Scenario S104 a HA should be FA." name="004"/>'
        add=''.join(f'\n            <VASSAL.build.module.folder.ModuleSubFolder desc="{d}" name="{n}"/>' for n,d in CHANGELOG)
        b.replace_raw(anchor, anchor+add, 'change log entries (beta18 / 005)')
    b.save(out); build_vmod('/home/claude/vmod/CCNapoleonics5_1_0DEV.vmod', out, vmod, version=VERSION if release else None)
    return b
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='alpha':
        b=apply(out='bf_alpha.xml', vmod='CCNapoleonics5_1_0alpha.vmod', release=True)
    else: b=apply()
    print('\n'.join(b.log))
