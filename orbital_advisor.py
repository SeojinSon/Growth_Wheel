#!/usr/bin/env python3
# orbital_advisor.py — 운파고
VERSION = "1.2.0"

# ════════════════════════════════════════════════════
#  ★ 업데이트 URL
UPDATE_URL = "https://raw.githubusercontent.com/SeojinSon/Growth_Wheel/refs/heads/main/orbital_advisor.py"
#  ★ Tesseract 경로
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# ════════════════════════════════════════════════════

import subprocess, sys, os, re, ssl, urllib.request, threading
from tkinter import messagebox
import tkinter as tk

def _install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    import customtkinter as ctk
except ImportError:
    print("customtkinter 설치 중..."); _install("customtkinter")
    import customtkinter as ctk

try:
    import mss
    MSS_OK = True
except ImportError:
    _install("mss")
    try:
        import mss
        MSS_OK = True
    except:
        MSS_OK = False

try:
    import pytesseract
    from PIL import ImageGrab, ImageEnhance, Image
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    OCR_OK = True
except ImportError:
    print("pytesseract/pillow 설치 중..."); _install("pytesseract"); _install("pillow")
    import pytesseract
    from PIL import ImageGrab, ImageEnhance, Image
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    OCR_OK = True

# ── 상수 ──────────────────────────────────────────────────────
ORBIT_CFG = {
    "star": {"name":"⭐ 별",   "slots":8,  "maxFills":5, "gems":["루비","토파즈","에메랄드"],                   "gemCount":3, "mainProb":0.222},
    "moon": {"name":"🌙 달",   "slots":10, "maxFills":7, "gems":["루비","토파즈","에메랄드","사파이어"],          "gemCount":4, "mainProb":0.167},
    "sun":  {"name":"☀️ 태양", "slots":12, "maxFills":8, "gems":["루비","토파즈","에메랄드","사파이어","자수정"], "gemCount":5, "mainProb":0.133},
}
FIXED_RATE = {1:0.9, 2:0.7, 3:0.4, 4:0.3, 5:0.2, 6:0.1}
RAND_RATE  = {1:0.9, 3:0.5, 5:0.3}
GEM_COLOR  = {"루비":"#FF5555","토파즈":"#FFB800","에메랄드":"#33CC66",
              "사파이어":"#4499FF","자수정":"#AA66FF","랜덤":"#888899","?":"#555566"}
GEM_BG     = {"루비":"#3D1515","토파즈":"#3D2E00","에메랄드":"#0D2E16",
              "사파이어":"#0D1A3D","자수정":"#1E0D3D","랜덤":"#2A2A2A","?":"#1A1A2A"}
GEM_HOVER  = {"루비":"#5A2020","토파즈":"#5A4400","에메랄드":"#1A4A28",
              "사파이어":"#1A2A5A","자수정":"#2E1A5A","랜덤":"#3A3A3A","?":"#2A2A3A"}
GEM_ALIASES = {
    "루비":    ["루비","루바","루이"],
    "토파즈":  ["토파즈","토파","토피즈","토파스"],
    "에메랄드":["에메랄드","에메","에메랄","에머랄드"],
    "사파이어":["사파이어","사파","사피이어","사파이"],
    "자수정":  ["자수정","자수","자수졍"],
    "랜덤":    ["랜덤","렌덤","랜","무작위","무작"],
}
TAG_COLOR = {"BEST":"#33CC66","GOOD":"#88CC44","OK":"#FFB800","NEUTRAL":"#888888","RISKY":"#FF8800","BAD":"#FF5555"}
TAG_LABEL = {"BEST":"최선 ✅✅","GOOD":"좋음 ✅","OK":"보통","NEUTRAL":"중립","RISKY":"위험 ⚠️","BAD":"나쁨 ❌"}

# ── 분석 엔진 ─────────────────────────────────────────────────
def get_rate(gem, count):
    return RAND_RATE.get(count, 0.3) if gem == "랜덤" else FIXED_RATE.get(count, 0.1)

def score_option(gem, count, cur, max_s, main, sub, gem_cnt):
    if not gem: return None
    sr   = get_rate(gem, count)
    end  = min(cur + count - 1, max_s)
    aff  = list(range(cur, end + 1))
    evs  = [s for s in aff if s % 2 == 0]
    odds = [s for s in aff if s % 2 == 1]
    if gem == main:
        if evs: return {"score":sr*(len(evs)*10+len(odds)*0.5),"verdict":f"짝수 {'+'.join(map(str,evs))}번 → 메인 {sr*100:.0f}%","tag":"BEST","evs":evs,"odds":odds}
        return {"score":1,"verdict":"홀수만 채움 (OK)","tag":"OK","evs":evs,"odds":odds}
    if gem == "랜덤":
        p = 1/gem_cnt; score = sr*(len(evs)*10*p+len(odds)*p)
        if evs: return {"score":score,"verdict":f"짝수포함 랜덤 — 메인 기대 {sr*len(evs)*p*100:.1f}%","tag":"RISKY","evs":evs,"odds":odds}
        return {"score":score,"verdict":"홀수만 랜덤 채움","tag":"OK","evs":evs,"odds":odds}
    if sub and sub != "상관없음" and gem == sub:
        if evs: return {"score":-5,"verdict":f"짝수 {'+'.join(map(str,evs))}번에 부보석 침범 ❌","tag":"BAD","evs":evs,"odds":odds}
        return {"score":sr*len(odds)*3,"verdict":"홀수에 부보석 ✅","tag":"GOOD","evs":evs,"odds":odds}
    if evs: return {"score":-8,"verdict":f"짝수 {'+'.join(map(str,evs))}번에 잘못된 보석 ❌","tag":"BAD","evs":evs,"odds":odds}
    return {"score":sr*len(odds)*0.5,"verdict":"홀수만 채움","tag":"NEUTRAL","evs":evs,"odds":odds}

def get_recommendation(analyses, cur, ref_left, is_even, main_prob):
    valid = [(i,a) for i,a in enumerate(analyses) if a]
    if not valid: return None
    best_i, best_a = max(valid, key=lambda x: x[1]["score"])
    p_good = 1-(1-main_prob)**3; refresh_ev = p_good*(9 if is_even else 3)*0.7
    if best_a["score"] <= 0 and ref_left > 0: return {"type":"refresh","msg":"좋은 옵션이 없어요. 새로고침!","idx":None}
    if is_even and best_a["score"] < refresh_ev and ref_left > 0: return {"type":"refresh","msg":f"새로고침 기대값({refresh_ev:.1f}) > 현재 최선({best_a['score']:.1f}). 새로고침!","idx":None}
    if best_a["score"] < 0: return {"type":"warn","msg":"모든 옵션이 짝수를 망칩니다. 새로고침이 없으면 덜 나쁜 것 선택.","idx":best_i}
    return {"type":"pick","msg":best_a["verdict"],"idx":best_i}

# ── OCR 파싱 ──────────────────────────────────────────────────
def detect_gem(text):
    for gem, aliases in GEM_ALIASES.items():
        if any(a in text for a in aliases):
            return gem
    return None

def preprocess_img(img):
    w, h = img.size
    img = img.resize((w*2, h*2), Image.LANCZOS)
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.5)
    img = img.point(lambda x: 255 if x > 100 else 0)
    return img

def parse_ocr_text(text):
    results = []
    lines = [l.strip() for l in text.replace('\n\n','\n').split('\n') if l.strip()]
    for line in lines:
        count_m = re.search(r'(\d+)개', line)
        gem = detect_gem(line)
        if gem and count_m:
            count = int(count_m.group(1))
            if 1 <= count <= 6:
                results.append((gem, count))
    return results

# ── 업데이트 ──────────────────────────────────────────────────
def fetch_update(callback):
    def _w():
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
            with urllib.request.urlopen(UPDATE_URL, timeout=10, context=ctx) as r:
                code = r.read().decode("utf-8")
            ver = "0.0.0"
            for line in code.splitlines():
                if line.startswith("VERSION = "): ver=line.split('"')[1]; break
            callback("ok", code, ver)
        except Exception as e: callback("err", str(e), None)
    threading.Thread(target=_w, daemon=True).start()

def apply_update(new_code):
    path=os.path.abspath(__file__); tmp=path+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: f.write(new_code)
    os.replace(tmp, path)
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw): pythonw = sys.executable
    subprocess.Popen([pythonw, path]); sys.exit(0)

# ── 화면 감시 ─────────────────────────────────────────────────
class ScreenWatcher:
    def __init__(self, region, on_change):
        self.region   = region   # (x1, y1, x2, y2)
        self.on_change = on_change
        self.running  = False
        self._last    = None

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _diff(self, img1, img2):
        a = list(img1.resize((30,30)).convert('L').getdata())
        b = list(img2.resize((30,30)).convert('L').getdata())
        return sum(abs(x-y) for x,y in zip(a,b)) / (len(a)*255)

    def _loop(self):
        import time
        while self.running:
            try:
                x1,y1,x2,y2 = self.region
                img = ImageGrab.grab(bbox=(x1,y1,x2,y2))
                if self._last is not None:
                    if self._diff(img, self._last) > 0.06:
                        self._last = img
                        self.on_change(img)
                        time.sleep(2.5)  # 감지 후 쿨다운
                        continue
                self._last = img
            except Exception:
                pass
            import time as _t; _t.sleep(1)

# ── 앱 ────────────────────────────────────────────────────────
class App(ctk.CTk):
    BG="#070B14"; CARD="#0D1525"; BORDER="#1C2A40"; GOLD="#C9A84C"; TEXT="#D8DFF0"; MUTED="#5A7090"

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark"); ctk.set_default_color_theme("blue")
        self.configure(fg_color=self.BG)
        self.title(f"운파고  v{VERSION}"); self.geometry("740x820"); self.minsize(620,600)
        self._init_state(); self._build_chrome(); self._render()

    def _init_state(self):
        self.phase="orbit"; self.orbit=None; self.main_gem=None; self.sub_gem=None
        self.cur_slot=1; self.sel_left=10; self.ref_left=5; self.slot_map={}
        self.opt_gems=["","",""]; self.opt_counts=[1,1,1]
        self.pending_idx=None; self.analyses=[None,None,None]; self.rec=None
        self.watch_region=None; self.watcher=None; self.watching=False

    def _build_chrome(self):
        bar=ctk.CTkFrame(self, fg_color="#0D1525", height=52, corner_radius=0)
        bar.pack(fill="x"); bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="✦ 운파고 ✦", font=ctk.CTkFont(size=18,weight="bold"),
                     text_color=self.GOLD).pack(side="left", padx=16)
        ctk.CTkLabel(bar, text=f"v{VERSION}", font=ctk.CTkFont(size=10),
                     text_color="#2A3A55").pack(side="right", padx=4)
        self._upd_btn=ctk.CTkButton(bar, text="🔄 업데이트", width=100, height=32,
            fg_color="#1C2A40", hover_color="#2A3A55", text_color="#4499FF",
            corner_radius=6, command=self._on_update)
        self._upd_btn.pack(side="right", padx=8)
        self._home_btn=ctk.CTkButton(bar, text="🏠 홈", width=72, height=32,
            fg_color="#1C2A40", hover_color="#2A3A55", text_color=self.MUTED,
            corner_radius=6, command=self._go_home)
        self._home_btn.pack(side="right", padx=4)
        self.scroll=ctk.CTkScrollableFrame(self, fg_color=self.BG, scrollbar_button_color="#1C2A40")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=8)

    def _render(self):
        for w in self.scroll.winfo_children(): w.destroy()
        self.rec=None; self.pending_idx=None
        # 홈 버튼: 메인(orbit) 페이지에서는 숨기기
        if self.phase == "orbit":
            self._home_btn.pack_forget()
        else:
            self._home_btn.pack(side="right", padx=4)
        getattr(self, f"_page_{self.phase}")()

    def _card(self, **kw):
        f=ctk.CTkFrame(self.scroll, fg_color=self.CARD, corner_radius=10,
                       border_width=1, border_color=self.BORDER, **kw)
        f.pack(fill="x", padx=2, pady=4); return f

    def _lbl(self, p, text, size=14, color=None, bold=False, **kw):
        return ctk.CTkLabel(p, text=text,
            font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
            text_color=color or self.TEXT, **kw)

    def _sec(self, p, text):
        ctk.CTkLabel(p, text=text.upper(), font=ctk.CTkFont(size=12),
                     text_color=self.MUTED).pack(anchor="w", padx=12, pady=(10,2))

    def _go(self, phase): self.phase=phase; self._render()

    def _gem_btn(self, parent, gem, cmd):
        c=GEM_COLOR.get(gem,"#888"); bg=GEM_BG.get(gem,"#1C2A40"); hv=GEM_HOVER.get(gem,"#2A3A55")
        ctk.CTkButton(parent, text=gem, width=96, height=42,
            fg_color=bg, hover_color=hv, text_color=c,
            border_width=1, border_color=c, corner_radius=8,
            font=ctk.CTkFont(size=14),
            command=cmd).pack(side="left", padx=4, pady=4)

    def _slot_grid(self, parent):
        cfg=ORBIT_CFG[self.orbit]
        row=ctk.CTkFrame(parent, fg_color="transparent"); row.pack(padx=8, pady=8)
        for n in range(1, cfg["slots"]+1):
            ev=n%2==0; gem=self.slot_map.get(n); cur=n==self.cur_slot
            gc=GEM_COLOR.get(gem,"#444") if gem else "#444"
            sz=46 if ev else 35
            fg=GEM_BG.get(gem,"#0A1020") if gem else ("#1A2A40" if cur else "#0A1020")
            bd="#C9A84C" if cur else (gc if gem else ("#2A3A55" if ev else "#1A2535"))
            bw=2 if cur else (2 if ev else 1)
            txt=(gem[:2] if gem and gem!="?" else ("?" if gem else str(n)))
            sub_txt="✓" if ev and gem==self.main_gem else ""
            ctk.CTkButton(row, text=f"{txt}\n{sub_txt}", width=sz, height=sz,
                fg_color=fg, hover_color=fg,
                text_color=gc if gem else ("#C9A84C" if cur else "#334455"),
                border_width=bw, border_color=bd, corner_radius=sz//2,
                font=ctk.CTkFont(size=12), state="disabled").pack(side="left", padx=2)

    # ── 페이지들 ──────────────────────────────────────────────
    def _page_orbit(self):
        self._sec(self.scroll, "궤도 선택")
        for oid,cfg in ORBIT_CFG.items():
            ctk.CTkButton(self.scroll,
                text=f"{cfg['name']}     슬롯 {cfg['slots']}개  ·  보석 {len(cfg['gems'])}종  ·  최대 {cfg['maxFills']}개/슬롯",
                font=ctk.CTkFont(size=15), height=54, anchor="w",
                fg_color=self.CARD, hover_color="#1C2A40", text_color=self.TEXT,
                border_width=1, border_color=self.BORDER, corner_radius=8,
                command=lambda o=oid: self._sel_orbit(o)).pack(fill="x", padx=2, pady=3)

    def _sel_orbit(self, oid): self.orbit=oid; self._go("main")

    def _page_main(self):
        ctk.CTkButton(self.scroll, text="← 뒤로", width=72, height=28,
            fg_color="transparent", hover_color=self.BORDER, text_color=self.MUTED,
            command=lambda: self._go("orbit")).pack(anchor="w", padx=4, pady=(2,0))
        cfg=ORBIT_CFG[self.orbit]; card=self._card()
        self._sec(card, f"{cfg['name']} — 메인 보석 (짝수 슬롯)")
        row=ctk.CTkFrame(card, fg_color="transparent"); row.pack(padx=8, pady=(4,12))
        for g in cfg["gems"]: self._gem_btn(row, g, cmd=lambda gem=g: self._sel_main(gem))

    def _sel_main(self, gem): self.main_gem=gem; self._go("sub")

    def _page_sub(self):
        ctk.CTkButton(self.scroll, text="← 뒤로", width=72, height=28,
            fg_color="transparent", hover_color=self.BORDER, text_color=self.MUTED,
            command=lambda: self._go("main")).pack(anchor="w", padx=4, pady=(2,0))
        cfg=ORBIT_CFG[self.orbit]; card=self._card()
        self._lbl(card, f"메인 보석: {self.main_gem}", size=12,
                  color=GEM_COLOR.get(self.main_gem,"#888")).pack(anchor="w", padx=12, pady=(10,2))
        self._sec(card, f"부 보석 선택 (홀수 슬롯, {self.main_gem} 제외)")
        row=ctk.CTkFrame(card, fg_color="transparent"); row.pack(padx=8, pady=(4,12))
        for g in cfg["gems"]:
            if g!=self.main_gem: self._gem_btn(row, g, cmd=lambda gem=g: self._sel_sub(gem))
        ctk.CTkButton(row, text="상관없음", width=88, height=38,
            fg_color="#1C2A40", hover_color="#2A3A55", text_color=self.MUTED,
            border_width=1, border_color="#2A3A55", corner_radius=8,
            command=lambda: self._sel_sub("상관없음")).pack(side="left", padx=4, pady=4)

    def _sel_sub(self, gem):
        self.sub_gem=gem; self.cur_slot=1; self.sel_left=10; self.ref_left=5
        self.slot_map={}; self.opt_gems=["","",""]; self.opt_counts=[1,1,1]; self._go("paint")

    def _page_paint(self):
        cfg=ORBIT_CFG[self.orbit]; max_s=cfg["slots"]
        is_even=self.cur_slot%2==0
        ev_list=[s for s in range(1,max_s+1) if s%2==0]
        main_cnt=sum(1 for s in ev_list if self.slot_map.get(s)==self.main_gem)

        # 뒤로가기
        ctk.CTkButton(self.scroll, text="← 뒤로", width=72, height=28,
            fg_color="transparent", hover_color=self.BORDER, text_color=self.MUTED,
            command=self._back_to_setup).pack(anchor="w", padx=4, pady=(2,0))

        sbar=self._card()
        row=ctk.CTkFrame(sbar, fg_color="transparent"); row.pack(fill="x", padx=12, pady=10)
        slot_txt=f"슬롯 {self.cur_slot}  {'🎯 짝수' if is_even else '홀수'}" if self.cur_slot<=max_s else "✓ 전체 완료"
        self._lbl(row, slot_txt, size=17, color="#33CC66" if is_even else "#FFB800", bold=True).pack(side="left")
        self._lbl(row, f"선택 {self.sel_left}회", size=14, color=self.GOLD).pack(side="right", padx=12)
        self._lbl(row, f"새로고침 {self.ref_left}/5", size=14,
                  color="#4499FF" if self.ref_left>0 else "#334").pack(side="right", padx=4)

        gc=self._card()
        self._sec(gc, f"슬롯 현황  |  {self.main_gem} {main_cnt}/{len(ev_list)}"); self._slot_grid(gc)

        if self.pending_idx is None and self.cur_slot<=max_s: self._build_opt_panel(cfg)
        if self.pending_idx is not None: self._build_pending_panel()

    def _build_opt_panel(self, cfg):
        oc=self._card(); self._sec(oc, "선택지 입력")
        self._opt_rate_lbls=[]; self._opt_tag_lbls=[]; self._opt_gem_vars=[]; self._opt_cnt_vars=[]

        for i in range(3):
            row=ctk.CTkFrame(oc, fg_color="transparent"); row.pack(fill="x", padx=10, pady=3)
            self._lbl(row, f"{i+1}.", size=14, color=self.MUTED).pack(side="left", padx=(0,6))
            gv=ctk.StringVar(value=self.opt_gems[i] or "-- 보석 --")
            ctk.CTkOptionMenu(row, variable=gv, values=["-- 보석 --"]+cfg["gems"]+["랜덤"],
                width=130, height=34, fg_color="#0A1020", button_color=self.BORDER,
                button_hover_color="#2A3A55", dropdown_fg_color="#0D1525",
                font=ctk.CTkFont(size=14),
                command=lambda v,idx=i: self._gem_changed(idx)).pack(side="left", padx=4)
            self._opt_gem_vars.append(gv)
            cv=ctk.StringVar(value=str(self.opt_counts[i]))
            ctk.CTkOptionMenu(row, variable=cv, values=["1","2","3","4","5","6"],
                width=74, height=34, fg_color="#0A1020", button_color=self.BORDER,
                button_hover_color="#2A3A55", dropdown_fg_color="#0D1525",
                font=ctk.CTkFont(size=14),
                command=lambda v,idx=i: self._cnt_changed(idx)).pack(side="left", padx=4)
            self._opt_cnt_vars.append(cv)
            rl=self._lbl(row,"",size=13,color=self.GOLD); rl.pack(side="left",padx=6)
            tl=self._lbl(row,"",size=13,color="#888"); tl.pack(side="left",padx=2)
            self._opt_rate_lbls.append(rl); self._opt_tag_lbls.append(tl)

        self._refresh_opt_labels(cfg)

        br=ctk.CTkFrame(oc, fg_color="transparent"); br.pack(fill="x", padx=10, pady=(10,12))
        ctk.CTkButton(br, text="📷 캡처", width=80, height=34,
            fg_color="#1C3A1C", hover_color="#2A5A2A", text_color="#33CC66",
            border_width=1, border_color="#33CC66",
            command=self._start_capture).pack(side="left", padx=4)

        watch_color = "#FF5555" if self.watching else "#AA66FF"
        watch_text  = "🔴 감지 중" if self.watching else "📡 자동 감지"
        watch_fg    = "#3A1515" if self.watching else "#1E0D3D"
        ctk.CTkButton(br, text=watch_text, height=34,
            fg_color=watch_fg, hover_color="#2A1A3A", text_color=watch_color,
            border_width=1, border_color=watch_color,
            command=self._toggle_watch).pack(side="left", padx=4)
        ctk.CTkButton(br, text="🔍 분석", width=80, height=34,
            fg_color="#2A2010", hover_color="#3A3010", text_color=self.GOLD,
            border_width=1, border_color=self.GOLD, command=self._analyze).pack(side="left", padx=4)
        if self.ref_left>0:
            ctk.CTkButton(br, text=f"🔄 새로고침 ({self.ref_left})", height=34,
                fg_color="#1C2A40", hover_color="#2A3A55", text_color="#4499FF",
                border_width=1, border_color="#4499FF",
                command=self._do_refresh).pack(side="left", padx=4)
        ctk.CTkButton(br, text="→ 리버스 단계", height=34,
            fg_color=self.BORDER, hover_color="#2A3A55", text_color=self.MUTED,
            command=lambda: self._go("reverse")).pack(side="right", padx=4)

        if self.rec: self._build_rec_panel()

    def _refresh_opt_labels(self, cfg):
        for i in range(3):
            gem=self.opt_gems[i]; count=self.opt_counts[i]
            if gem:
                r=get_rate(gem,count); self._opt_rate_lbls[i].configure(text=f"{r*100:.0f}%")
                a=score_option(gem,count,self.cur_slot,cfg["slots"],
                               self.main_gem,self.sub_gem or "상관없음",cfg["gemCount"])
                self.analyses[i]=a
                if a: self._opt_tag_lbls[i].configure(text=TAG_LABEL.get(a["tag"],""),
                                                       text_color=TAG_COLOR.get(a["tag"],"#888"))
                else: self._opt_tag_lbls[i].configure(text="")
            else:
                self._opt_rate_lbls[i].configure(text=""); self._opt_tag_lbls[i].configure(text="")
                self.analyses[i]=None

    def _gem_changed(self, idx):
        v=self._opt_gem_vars[idx].get(); self.opt_gems[idx]="" if v=="-- 보석 --" else v
        self.rec=None; self._refresh_opt_labels(ORBIT_CFG[self.orbit])

    def _cnt_changed(self, idx):
        self.opt_counts[idx]=int(self._opt_cnt_vars[idx].get())
        self.rec=None; self._refresh_opt_labels(ORBIT_CFG[self.orbit])

    def _analyze(self):
        cfg=ORBIT_CFG[self.orbit]
        self.analyses=[score_option(self.opt_gems[i],self.opt_counts[i],self.cur_slot,
            cfg["slots"],self.main_gem,self.sub_gem or "상관없음",cfg["gemCount"])
            if self.opt_gems[i] else None for i in range(3)]
        self.rec=get_recommendation(self.analyses,self.cur_slot,self.ref_left,
                                    self.cur_slot%2==0,cfg["mainProb"])
        self._render()

    def _build_rec_panel(self):
        r=self.rec
        type_map={"refresh":("#FFB800","🔄 새로고침 권장!"),
                  "pick":("#33CC66",f"✅ 옵션 {r['idx']+1} 선택!"),
                  "warn":("#FF8800","⚠️ 주의")}
        color,title=type_map.get(r["type"],("#888",""))
        rc=ctk.CTkFrame(self.scroll, fg_color=self.CARD, corner_radius=10,
                        border_width=1, border_color=color)
        rc.pack(fill="x", padx=2, pady=4)
        self._lbl(rc, title, size=15, color=color, bold=True).pack(anchor="w", padx=12, pady=(10,2))
        self._lbl(rc, r["msg"], size=13, color="#A0AABB").pack(anchor="w", padx=12, pady=(0,8))
        br=ctk.CTkFrame(rc, fg_color="transparent"); br.pack(anchor="w", padx=12, pady=(0,12))
        if r["type"]=="pick" and r["idx"] is not None:
            ctk.CTkButton(br, text=f"옵션 {r['idx']+1} 선택", height=32,
                fg_color=self.BORDER, hover_color="#2A3A55", text_color=color,
                border_width=1, border_color=color,
                command=lambda: self._pick(r["idx"])).pack(side="left", padx=4)
        if r["type"]=="refresh" and self.ref_left>0:
            ctk.CTkButton(br, text="새로고침", height=32,
                fg_color="#1C2A40", hover_color="#2A3A55", text_color="#4499FF",
                border_width=1, border_color="#4499FF",
                command=self._do_refresh).pack(side="left", padx=4)
        for i in range(3):
            if self.opt_gems[i] and i!=r.get("idx"):
                ctk.CTkButton(br, text=f"옵션 {i+1}", width=72, height=32,
                    fg_color=self.BORDER, hover_color="#2A3A55", text_color=self.MUTED,
                    command=lambda idx=i: self._pick(idx)).pack(side="left", padx=4)

    def _build_pending_panel(self):
        g=self.opt_gems[self.pending_idx]; c=self.opt_counts[self.pending_idx]; r=get_rate(g,c)
        pc=self._card()
        self._lbl(pc, f"옵션 {self.pending_idx+1}  ({g}  {c}개  ·  {r*100:.0f}%)  결과는?",
                  size=15, color=self.GOLD).pack(padx=12, pady=(12,8))
        br=ctk.CTkFrame(pc, fg_color="transparent"); br.pack(padx=12, pady=(0,12))
        ctk.CTkButton(br, text="✅ 성공!", width=110, height=38,
            fg_color="#1A3A1A", hover_color="#2A5A2A", text_color="#33CC66",
            border_width=1, border_color="#33CC66",
            command=lambda: self._result(True)).pack(side="left", padx=6)
        ctk.CTkButton(br, text="❌ 실패", width=110, height=38,
            fg_color="#3A1A1A", hover_color="#5A2A2A", text_color="#FF5555",
            border_width=1, border_color="#FF5555",
            command=lambda: self._result(False)).pack(side="left", padx=6)

    def _pick(self, idx): self.pending_idx=idx; self._render()

    def _result(self, ok):
        cfg=ORBIT_CFG[self.orbit]; gem=self.opt_gems[self.pending_idx]; count=self.opt_counts[self.pending_idx]
        self.sel_left-=1
        if ok:
            end=min(self.cur_slot+count-1, cfg["slots"])
            for s in range(self.cur_slot, end+1): self.slot_map[s]=gem if gem!="랜덤" else "?"
            self.cur_slot=end+1
            if self.cur_slot>cfg["slots"] or self.sel_left==0:
                self._reset_opts(); self._go("reverse"); return
        self._reset_opts(); self._render()

    def _reset_opts(self):
        self.opt_gems=["","",""]; self.opt_counts=[1,1,1]
        self.pending_idx=None; self.rec=None; self.analyses=[None,None,None]

    def _go_home(self):
        if self.phase in ("orbit","main","sub"):
            self._stop_watch(); self._init_state(); self._go("orbit")
        else:
            if messagebox.askyesno("홈으로","현재 진행 상황이 초기화돼요.\n홈으로 돌아갈까요?"):
                self._stop_watch(); self._init_state(); self._go("orbit")

    def _back_to_setup(self):
        if messagebox.askyesno("설정 변경", "현재 진행 상황이 초기화돼요.\n설정을 변경할까요?"):
            self._init_state(); self._go("orbit")

    def _do_refresh(self): self.ref_left-=1; self._reset_opts(); self._render()

    # ── 캡처 기능 ─────────────────────────────────────────────
    def _start_capture(self):
        self.withdraw()
        self.after(400, self._show_overlay)

    def _show_overlay(self, watch_mode=False):
        overlay=tk.Toplevel()
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.35)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="gray10")

        msg = "📡  자동 감지 영역을 드래그하세요  |  ESC: 취소" if watch_mode else "📷  선택지 3개가 있는 영역을 드래그하세요  |  ESC: 취소"
        tk.Label(overlay, text=msg, fg="yellow", bg="gray10",
                 font=("맑은 고딕", 13)).place(relx=0.5, rely=0.02, anchor="center")

        canvas=tk.Canvas(overlay, cursor="cross", bg="gray10", highlightthickness=0)
        canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        state={"start":None, "rect":None}

        def on_press(e):
            state["start"]=(e.x,e.y)
            if state["rect"]: canvas.delete(state["rect"])
            state["rect"]=canvas.create_rectangle(e.x,e.y,e.x,e.y,outline="#FFD700",width=2)

        def on_drag(e):
            if state["start"] and state["rect"]:
                sx,sy=state["start"]; canvas.coords(state["rect"],sx,sy,e.x,e.y)

        def on_release(e):
            if state["start"]:
                sx,sy=state["start"]; ex,ey=e.x,e.y
                overlay.destroy(); self.deiconify()
                x1,y1=min(sx,ex),min(sy,ey); x2,y2=max(sx,ex),max(sy,ey)
                if x2-x1>20 and y2-y1>20:
                    if watch_mode:
                        self.after(150, lambda: self._start_watch_with_region((x1,y1,x2,y2)))
                    else:
                        self.after(150, lambda: self._run_ocr(x1,y1,x2,y2))

        def on_esc(e): overlay.destroy(); self.deiconify()
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        overlay.bind("<Escape>", on_esc)
        overlay.focus_force()

    def _run_ocr(self, x1, y1, x2, y2):
        try:
            img=ImageGrab.grab(bbox=(x1,y1,x2,y2))
            img=preprocess_img(img)
            text=pytesseract.image_to_string(img, lang="kor", config="--psm 6")
            results=parse_ocr_text(text)

            if not results:
                messagebox.showwarning("인식 실패", "선택지를 인식하지 못했어요.\n선택지 텍스트 부분만 정확히 드래그해 주세요!")
                return

            # 최대 3개 채우기
            for i, (gem, count) in enumerate(results[:3]):
                self.opt_gems[i]=gem; self.opt_counts[i]=count

            self._render()
        except Exception as e:
            messagebox.showerror("OCR 오류", f"오류가 발생했어요:\n{str(e)}")

    def _toggle_watch(self):
        if self.watching:
            self._stop_watch()
        else:
            if self.watch_region:
                self._start_watch_with_region(self.watch_region)
            else:
                # 처음엔 영역 지정 필요
                self._start_capture_for_watch()

    def _start_capture_for_watch(self):
        self.withdraw()
        self.after(400, lambda: self._show_overlay(watch_mode=True))

    def _start_watch_with_region(self, region):
        self.watch_region = region
        self.watching = True
        self.watcher = ScreenWatcher(region, self._on_screen_change)
        self.watcher.start()
        self._render()

    def _stop_watch(self):
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
        self.watching = False
        self._render()

    def _on_screen_change(self, img):
        """화면 변화 감지 시 자동 OCR"""
        try:
            processed = preprocess_img(img)
            text = pytesseract.image_to_string(processed, lang="kor", config="--psm 6")
            results = parse_ocr_text(text)
            if results:
                for i, (gem, count) in enumerate(results[:3]):
                    self.opt_gems[i] = gem
                    self.opt_counts[i] = count
                self.after(0, self._render)
        except Exception:
            pass
    def _page_reverse(self):
        cfg=ORBIT_CFG[self.orbit]; max_s=cfg["slots"]
        ev_list=[s for s in range(1,max_s+1) if s%2==0]
        main_cnt=sum(1 for s in ev_list if self.slot_map.get(s)==self.main_gem)
        need_fix=[s for s in ev_list if self.slot_map.get(s)!=self.main_gem]

        hc=self._card()
        self._lbl(hc, f"{cfg['name']}  —  리버스 체인지", size=15, color=self.GOLD, bold=True
                  ).pack(anchor="w", padx=12, pady=(12,4))
        self._lbl(hc, f"메인({self.main_gem}) 짝수 슬롯: {main_cnt}/{len(ev_list)}",
                  size=12, color="#33CC66" if main_cnt==len(ev_list) else "#FFB800"
                  ).pack(anchor="w", padx=12, pady=(0,10))

        gc=self._card(); self._sec(gc, "현재 슬롯 현황"); self._slot_grid(gc)

        if main_cnt==len(ev_list):
            done_card=self._card()
            self._lbl(done_card,"🎉 모든 짝수 슬롯에 메인 보석! 완료를 눌러주세요!",
                      size=13,color="#33CC66").pack(padx=12,pady=12)
        else:
            tc=self._card(); self._sec(tc, f"개선 필요: {', '.join(map(str,need_fix))}번 슬롯")
            for s in need_fix:
                lg=self.slot_map.get(s-1); rg=self.slot_map.get(s+1)
                tips=[]
                if lg==self.main_gem: tips.append(f"{s}번 왼쪽 교체 → {s-1}번({self.main_gem})→{s}번")
                if rg==self.main_gem: tips.append(f"{s}번 오른쪽 교체 → {s+1}번({self.main_gem})→{s}번")
                tip=" 또는 ".join(tips) if tips else "인접 슬롯에 메인 보석 없음"
                self._lbl(tc,f"  슬롯 {s}번: {tip}",size=11,color="#A0AABB"
                          ).pack(anchor="w",padx=12,pady=2)
            ctk.CTkLabel(tc,text="").pack(pady=2)

        gd=self._card(); self._sec(gd,"선택 판단 기준")
        for icon,color,text in [
            ("✅","#33CC66","방향 교체: 비메인 짝수 옆 홀수에 메인 보석이 있을 때"),
            ("✅","#33CC66","특정 슬롯 쌍 교체: 메인↔비메인 위치 바꿀 때"),
            ("⚠️","#FFB800","좌우 랜덤 재부여: 메인 짝수 슬롯도 바뀔 수 있음"),
            ("❌","#FF5555","모두 재부여 / 위치 랜덤 변경 / 다시 시작  — 절대 금지"),
        ]:
            r=ctk.CTkFrame(gd,fg_color="transparent"); r.pack(fill="x",padx=8,pady=2)
            self._lbl(r,icon,size=14,color=color).pack(side="left",padx=(4,8))
            self._lbl(r,text,size=13,color="#A0AABB").pack(side="left")
        ctk.CTkLabel(gd,text="").pack(pady=2)

        br=ctk.CTkFrame(self.scroll,fg_color="transparent"); br.pack(fill="x",padx=4,pady=8)
        ctk.CTkButton(br,text="← Paint 단계로",height=38,
            fg_color=self.BORDER,hover_color="#2A3A55",text_color=self.MUTED,
            command=lambda: self._go("paint")).pack(side="left",padx=4)
        ctk.CTkButton(br,text="완료! ✓",width=110,height=38,
            fg_color="#2A2010",hover_color="#3A3010",text_color=self.GOLD,
            border_width=1,border_color=self.GOLD,
            command=lambda: self._go("done")).pack(side="right",padx=4)

    def _page_done(self):
        cfg=ORBIT_CFG[self.orbit]
        ev_list=[s for s in range(1,cfg["slots"]+1) if s%2==0]
        main_cnt=sum(1 for s in ev_list if self.slot_map.get(s)==self.main_gem)
        pct=int(main_cnt/len(ev_list)*100) if ev_list else 0
        icon="🎊" if pct==100 else ("🎉" if pct>=75 else "👍")

        dc=self._card()
        self._lbl(dc,icon,size=48).pack(pady=(18,8))
        self._lbl(dc,"완료!",size=22,color=self.GOLD,bold=True).pack()
        self._lbl(dc,f"{cfg['name']}  —  {self.main_gem} {main_cnt}/{len(ev_list)}",size=14).pack(pady=6)
        self._lbl(dc,f"짝수 슬롯 달성률 {pct}%",size=12,color=self.MUTED).pack(pady=(0,16))
        gc=self._card(); self._slot_grid(gc)
        ctk.CTkButton(self.scroll,text="처음부터 다시",height=42,width=170,
            fg_color="#2A2010",hover_color="#3A3010",text_color=self.GOLD,
            border_width=1,border_color=self.GOLD,command=self._restart).pack(pady=14)

    def _restart(self): self._init_state(); self._render()

    def _on_update(self):
        self._upd_btn.configure(text="확인 중...", state="disabled")
        fetch_update(lambda s,d,v: self.after(0, lambda: self._update_done(s,d,v)))

    def _update_done(self, status, data, new_ver):
        self._upd_btn.configure(text="🔄 업데이트", state="normal")
        if status=="err": messagebox.showerror("오류", f"업데이트 확인 실패:\n{data}"); return

        def ver_tuple(v):
            try: return tuple(int(x) for x in v.split('.'))
            except: return (0,0,0)

        cur = ver_tuple(VERSION)
        new = ver_tuple(new_ver)

        if new > cur:
            if messagebox.askyesno("업데이트 발견",
                    f"새 버전: v{new_ver}  (현재 v{VERSION})\n업데이트할까요?\n(앱이 재시작됩니다)"):
                apply_update(data)
        else:
            messagebox.showinfo("최신 버전", f"이미 최신 버전이에요! (v{VERSION})")

if __name__ == "__main__":
    app=App(); app.mainloop()
