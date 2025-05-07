# betting-bot/utils/image_generator.py

import logging
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import time
import io # Make sure io is imported

logger = logging.getLogger(__name__)

# --- Sport Category Mapping (Defined Globally) ---
SPORT_CATEGORY_MAP = {
    "NBA": "BASKETBALL", "NCAAB": "BASKETBALL",
    "NFL": "FOOTBALL", "NCAAF": "FOOTBALL",
    "MLB": "BASEBALL", "NCAAB_BASEBALL": "BASEBALL", # Added for consistency if used
    "NHL": "HOCKEY",
    "MLS": "SOCCER", "EPL": "SOCCER", "LA LIGA": "SOCCER", "SERIE A": "SOCCER", "BUNDESLIGA": "SOCCER", "LIGUE 1": "SOCCER",
    "TENNIS": "TENNIS",
    "UFC": "MMA", "MMA": "MMA",
    "DARTS": "DARTS"
    # Add other leagues/sports as needed
}
DEFAULT_FALLBACK_SPORT_CATEGORY = "OTHER_SPORTS" # For leagues not in map

# Helper function to get sport category for path construction
def get_sport_category_for_path(league_name: str) -> str:
    """Gets the sport category string for use in paths, using the global map."""
    return SPORT_CATEGORY_MAP.get(str(league_name).upper(), DEFAULT_FALLBACK_SPORT_CATEGORY)

# --- Default Font/Asset Path Logic (Global Scope Helper) ---
def _determine_asset_paths():
    assets_dir_default = "betting-bot/static/"
    font_dir_name = 'fonts'
    logo_dir_name = 'logos'
    teams_subdir_name = 'teams'
    leagues_subdir_name = 'leagues'

    script_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(script_dir)
    potential_assets_dir = os.path.join(parent_dir, 'assets')
    potential_static_dir = os.path.join(parent_dir, 'static')

    final_assets_dir = None
    # Check for 'assets' first, then 'static'
    if os.path.isdir(potential_assets_dir):
        final_assets_dir = potential_assets_dir
    elif os.path.isdir(potential_static_dir):
        final_assets_dir = potential_static_dir
    else:
        # If neither is found relative to script, try using the default path
        if os.path.isdir(assets_dir_default):
             final_assets_dir = assets_dir_default
        else:
             final_assets_dir = os.path.join(os.getcwd(), 'assets')
             logger.warning(f"Could not find 'assets' or 'static' relative to script or default path. Assuming assets path: {final_assets_dir}")

    logger.info(f"Path determination logic targeting base: {final_assets_dir}")

    paths = {
        "ASSETS_DIR": final_assets_dir,
        "DEFAULT_FONT_PATH": os.path.join(final_assets_dir, font_dir_name, 'Roboto-Regular.ttf'),
        "DEFAULT_BOLD_FONT_PATH": os.path.join(final_assets_dir, font_dir_name, 'Roboto-Bold.ttf'),
        "DEFAULT_EMOJI_FONT_PATH_NOTO": os.path.join(final_assets_dir, font_dir_name, 'NotoEmoji-Regular.ttf'),
        "DEFAULT_EMOJI_FONT_PATH_SEGOE": os.path.join(final_assets_dir, font_dir_name, 'SegoeUIEmoji.ttf'),
        "LEAGUE_TEAM_BASE_DIR": os.path.join(final_assets_dir, logo_dir_name, teams_subdir_name),
        "LEAGUE_LOGO_BASE_DIR": os.path.join(final_assets_dir, logo_dir_name, leagues_subdir_name),
        "DEFAULT_LOCK_ICON_PATH": os.path.join(final_assets_dir, "lock_icon.png"),
        "DEFAULT_TEAM_LOGO_PATH": os.path.join(final_assets_dir, logo_dir_name, 'default_logo.png')
    }
    return paths

_PATHS = _determine_asset_paths()

# --- Font Loading (Global Scope) ---
try:
    _font_path = _PATHS["DEFAULT_FONT_PATH"]
    if not os.path.exists(_font_path):
        logger.warning(f"Default font '{_font_path}' not found. Falling back.")
        if os.name == 'nt': _font_path = 'C:\\Windows\\Fonts\\arial.ttf'
        else:
            _found = False
            for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf']:
                if os.path.exists(p): _font_path = p; _found=True; break
            if not _found: _font_path = 'arial.ttf'
    logger.info(f"Using regular font: {_font_path}")

    _bold_font_path = _PATHS["DEFAULT_BOLD_FONT_PATH"]
    if not os.path.exists(_bold_font_path):
        logger.warning(f"Default bold font '{_bold_font_path}' not found. Trying bold variant or falling back.")
        _bold_font_path_try = _font_path.replace("Regular", "Bold").replace(".ttf", "-Bold.ttf")
        if not os.path.exists(_bold_font_path_try): _bold_font_path_try = _font_path.replace(".ttf", "bd.ttf")
        if not os.path.exists(_bold_font_path_try): _bold_font_path_try = _font_path.replace(".ttf", "-Bold.otf")
        if os.path.exists(_bold_font_path_try): _bold_font_path = _bold_font_path_try
        else: _bold_font_path = _font_path; logger.info("Using regular font as bold fallback.")
    logger.info(f"Using bold font: {_bold_font_path}")

    _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_NOTO"]
    if not os.path.exists(_emoji_font_path):
        _emoji_font_path = _PATHS["DEFAULT_EMOJI_FONT_PATH_SEGOE"]
        if not os.path.exists(_emoji_font_path):
            logger.warning(f"Default Noto/Segoe emoji fonts not found. Falling back.")
            if os.name == 'nt': _emoji_font_path = 'C:\\Windows\\Fonts\\seguiemj.ttf'
            else:
                _found = False
                for p in ['/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', '/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf']:
                     if os.path.exists(p): _emoji_font_path = p; _found=True; break
                if not _found: _emoji_font_path = _font_path
    logger.info(f"Using emoji font: {_emoji_font_path}")

    font_m_18 = ImageFont.truetype(_font_path, 18)
    font_m_24 = ImageFont.truetype(_font_path, 24)
    font_b_18 = ImageFont.truetype(_bold_font_path, 18)
    font_b_24 = ImageFont.truetype(_bold_font_path, 24)
    font_b_36 = ImageFont.truetype(_bold_font_path, 36)
    try: font_b_28 = ImageFont.truetype(_bold_font_path, 28)
    except IOError: font_b_28 = font_b_24
    try: emoji_font_24 = ImageFont.truetype(_emoji_font_path, 24)
    except IOError: emoji_font_24 = font_m_24
    logger.info("Successfully loaded fonts globally for image_generator.")
except Exception as e:
    logger.critical(f"CRITICAL: Error loading required fonts: {e}", exc_info=True)
    font_m_18=font_m_24=font_b_18=font_b_24=font_b_36=font_b_28=emoji_font_24 = ImageFont.load_default()


class BetSlipGenerator:
    def __init__(self, font_path: Optional[str] = None, emoji_font_path: Optional[str] = None, assets_dir: Optional[str] = None):
        self.assets_dir = assets_dir or _PATHS["ASSETS_DIR"]
        self.font_path = font_path or _PATHS["DEFAULT_FONT_PATH"]
        self.bold_font_path = _PATHS["DEFAULT_BOLD_FONT_PATH"]
        self.emoji_font_path = emoji_font_path or _PATHS["DEFAULT_EMOJI_FONT_PATH_NOTO"]
        self.league_team_base_dir = _PATHS["LEAGUE_TEAM_BASE_DIR"]
        self.league_logo_base_dir = _PATHS["LEAGUE_LOGO_BASE_DIR"]
        os.makedirs(self.league_team_base_dir, exist_ok=True)
        os.makedirs(self.league_logo_base_dir, exist_ok=True)
        self._logo_cache = {}
        self._font_cache = {}
        self._lock_icon_cache = None
        self._max_cache_size = 100
        self._cache_expiry = 3600
        self._last_cache_cleanup = time.time()
        self.width = 800; self.leg_height = 120; self.header_height = 100; self.footer_height = 80
        self.padding = 20; self.logo_size = 60; self.image = None
        self.font_m_18=font_m_18; self.font_m_24=font_m_24; self.font_b_18=font_b_18; self.font_b_24=font_b_24
        self.font_b_28=font_b_28; self.font_b_36=font_b_36; self.emoji_font_24=emoji_font_24
        logger.info(f"BetSlipGenerator initialized with determined assets_dir: {self.assets_dir}")

    def _format_odds_with_sign(self, odds: Optional[Any]) -> str:
        if odds is None: return "N/A"
        try:
            odds_num = int(float(odds)); return f"+{odds_num}" if odds_num > 0 else str(odds_num)
        except (ValueError, TypeError): return "N/A"

    def _ensure_team_dir_exists(self, league: str) -> str:
        league_upper = league.upper()
        if league_upper.startswith("NCAA"):
            specific_sport = get_sport_category_for_path(league_upper)
            if specific_sport == DEFAULT_FALLBACK_SPORT_CATEGORY: specific_sport = "UNKNOWN_NCAA_SPORT"
            team_dir = os.path.join(self.league_team_base_dir, "NCAA", specific_sport)
        else:
            sport_category = get_sport_category_for_path(league_upper)
            team_dir = os.path.join(self.league_team_base_dir, sport_category, league_upper)
        os.makedirs(team_dir, exist_ok=True); return team_dir

    def _cleanup_cache(self):
        now = time.time()
        if now - self._last_cache_cleanup > 300:
            expired = [k for k, (_, ts) in self._logo_cache.items() if now - ts > self._cache_expiry]
            for k in expired: self._logo_cache.pop(k, None)
            self._last_cache_cleanup = now

    def _load_team_logo(self, team_name: str, league: str) -> Optional[Image.Image]:
        if not team_name or not league: return None
        try:
            cache_key=f"team_{team_name}_{league}"; now=time.time()
            if cache_key in self._logo_cache:
                logo, ts = self._logo_cache[cache_key]
                if now - ts <= self._cache_expiry: return logo
                else: del self._logo_cache[cache_key]
            team_dir=self._ensure_team_dir_exists(league)
            fname_base=team_name.lower().replace(" ", "_")
            logo_path=os.path.join(team_dir, f"{fname_base}.png")
            ### START LOGGING ###
            absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info(f"Attempting to load team logo: Path='{absolute_logo_path}', Exists={file_exists}") # Corrected Log Line
            ### END LOGGING ###
            logo=None
            if file_exists:
                try: logo = Image.open(absolute_logo_path).convert("RGBA")
                except Exception as e: logger.error(f"Err loading {absolute_logo_path}: {e}")
            if logo is None:
                default_path = _PATHS["DEFAULT_TEAM_LOGO_PATH"]; abs_default = os.path.abspath(default_path)
                if os.path.exists(abs_default):
                    try: logo = Image.open(abs_default).convert("RGBA"); logger.warning(f"Using default logo for {team_name} (path: {absolute_logo_path})")
                    except Exception as e: logger.error(f"Err loading default {abs_default}: {e}")
                else: logger.warning(f"Default team logo not found: {abs_default}")
            if logo:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size: self._logo_cache.pop(min(self._logo_cache, key=lambda k: self._logo_cache[k][1]), None)
                self._logo_cache[cache_key] = (logo, now)
                return logo
            logger.warning(f"Final: No logo loaded for {team_name} ({league}) path: {absolute_logo_path}")
            return None
        except Exception as e: logger.error(f"Err _load_team_logo {team_name} ({league}): {e}", exc_info=True); return None

    def _load_lock_icon(self) -> Optional[Image.Image]:
        if self._lock_icon_cache is None:
            try:
                path = _PATHS["DEFAULT_LOCK_ICON_PATH"]; abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    with Image.open(abs_path) as lock: self._lock_icon_cache = lock.convert("RGBA").resize((30, 30), Image.Resampling.LANCZOS).copy()
                else: logger.warning(f"Lock icon not found: {abs_path}")
            except Exception as e: logger.error(f"Err loading lock icon: {e}")
        return self._lock_icon_cache

    def _load_league_logo(self, league: str) -> Optional[Image.Image]:
        if not league: return None
        try:
            cache_key=f"league_{league}"; now=time.time()
            if cache_key in self._logo_cache:
                logo, ts = self._logo_cache[cache_key]
                if now - ts <= self._cache_expiry: return logo
                else: del self._logo_cache[cache_key]
            sport=get_sport_category_for_path(league.upper())
            fname=f"{league.lower().replace(' ', '_')}.png"
            logo_dir=os.path.join(self.league_logo_base_dir, sport)
            logo_path=os.path.join(logo_dir, fname)
            os.makedirs(logo_dir, exist_ok=True)
            ### START LOGGING ###
            absolute_logo_path = os.path.abspath(logo_path)
            file_exists = os.path.exists(absolute_logo_path)
            logger.info(f"Attempting to load league logo: Path='{absolute_logo_path}', Exists={file_exists}") # Corrected Log Line
            ### END LOGGING ###
            logo=None
            if file_exists:
                try:
                    with Image.open(absolute_logo_path) as img: logo = img.convert('RGBA')
                except Exception as e: logger.error(f"Err loading {absolute_logo_path}: {e}")
            if logo:
                self._cleanup_cache()
                if len(self._logo_cache) >= self._max_cache_size: self._logo_cache.pop(min(self._logo_cache, key=lambda k: self._logo_cache[k][1]), None)
                self._logo_cache[cache_key] = (logo.copy(), now)
                return logo
            logger.warning(f"No logo found for league {league} (path: {absolute_logo_path})")
            return None
        except Exception as e: logger.error(f"Err _load_league_logo {league}: {e}", exc_info=True); return None

    def generate_bet_slip(
        self, home_team: str, away_team: str, league: Optional[str], line: str, odds: float,
        units: float, bet_id: str, timestamp: datetime, bet_type: str = "straight",
        parlay_legs: Optional[List[Dict[str, Any]]] = None, is_same_game: bool = False
    ) -> Optional[Image.Image]:
        eff_league=league or "UNKNOWN"; logger.info(f"Gen slip: {bet_type}, Lg: {eff_league}, ID: {bet_id}")
        try:
            width=800; header_h=100; footer_h=80; leg_h=180; num_legs=len(parlay_legs) if parlay_legs else 1
            if bet_type=="parlay" and parlay_legs: content_h=num_legs*leg_h; parlay_tot_h=120
            else: content_h=400; parlay_tot_h=0
            height = header_h + content_h + parlay_tot_h + footer_h
            img=Image.new('RGBA', (width, height), (40,40,40,255)); draw=ImageDraw.Draw(img)
            # Header
            h_y=30; title=f"{eff_league.upper()} - {'Same Game Parlay' if bet_type=='parlay' and is_same_game else 'Multi-Team Parlay Bet' if bet_type=='parlay' else 'Straight Bet'}"
            lg_logo=self._load_league_logo(eff_league)
            if lg_logo:
                r=min(60/lg_logo.height,1); nw=int(lg_logo.width*r); nh=int(lg_logo.height*r)
                lg_disp=lg_logo.resize((nw,nh),Image.Resampling.LANCZOS); lx=(width-nw)//2; ly=h_y-10
                if img.mode!='RGBA': img=img.convert("RGBA"); tmp=Image.new('RGBA',img.size,(0,0,0,0)); tmp.paste(lg_disp,(lx,ly),lg_disp); img=Image.alpha_composite(img,tmp); draw=ImageDraw.Draw(img); h_y+=nh+5
            else: h_y+=10
            bbox=draw.textbbox((0,0),title,self.font_b_36); tw=bbox[2]-bbox[0]; draw.text(((width-tw)/2,h_y),title,'white',self.font_b_36)
            # Content
            c_start_y=header_h+10
            if bet_type=="straight":
                logo_y=c_start_y+40; l_sz=(120,120)
                h_logo=self._load_team_logo(home_team,eff_league); a_logo=self._load_team_logo(away_team,eff_league)
                if h_logo: h_disp=h_logo.resize(l_sz,Image.Resampling.LANCZOS); if img.mode!='RGBA': img=img.convert("RGBA"); tmp=Image.new('RGBA',img.size,(0,0,0,0)); tmp.paste(h_disp,(width//4-l_sz[0]//2,logo_y),h_disp); img=Image.alpha_composite(img,tmp); draw=ImageDraw.Draw(img)
                draw.text((width//4,logo_y+l_sz[1]+20),home_team,'white',self.font_b_24,anchor='mm')
                if a_logo: a_disp=a_logo.resize(l_sz,Image.Resampling.LANCZOS); if img.mode!='RGBA': img=img.convert("RGBA"); tmp=Image.new('RGBA',img.size,(0,0,0,0)); tmp.paste(a_disp,(3*width//4-l_sz[0]//2,logo_y),a_disp); img=Image.alpha_composite(img,tmp); draw=ImageDraw.Draw(img)
                draw.text((3*width//4,logo_y+l_sz[1]+20),away_team,'white',self.font_b_24,anchor='mm')
                det_y=logo_y+l_sz[1]+80; bet_txt=f"{home_team}: {line}"; draw.text((width//2,det_y),bet_txt,'white',self.font_m_24,anchor='mm')
                sep_y=det_y+40; draw.line([(20,sep_y),(width-20,sep_y)],'white',2)
                odds_y=sep_y+30; odds_txt=self._format_odds_with_sign(odds); draw.text((width//2,odds_y),odds_txt,'white',self.font_b_24,anchor='mm')
                units_y=odds_y+50; units_txt=f"To Win {units:.2f} Units"; bbox=draw.textbbox((0,0),units_txt,self.font_b_24); u_w=bbox[2]-bbox[0]
                lock=self._load_lock_icon()
                if lock:
                    sp=20; t_w=u_w+2*lock.width+2*sp; sx=(width-t_w)//2
                    if img.mode!='RGBA': img=img.convert('RGBA'); tmp=Image.new('RGBA',img.size,(0,0,0,0)); tmp.paste(lock,(sx,int(units_y-lock.height/2)),lock); img=Image.alpha_composite(img,tmp); draw=ImageDraw.Draw(img)
                    tx=sx+lock.width+sp; draw.text((tx+u_w/2,units_y),units_txt,(255,215,0),self.font_b_24,"mm")
                    tmp=Image.new('RGBA',img.size,(0,0,0,0)); tmp.paste(lock,(int(tx+u_w+sp),int(units_y-lock.height/2)),lock); img=Image.alpha_composite(img,tmp); draw=ImageDraw.Draw(img)
                else: draw.text((width//2,units_y),units_txt,(255,215,0),self.font_b_24,'mm')
            elif bet_type=="parlay" and parlay_legs:
                curr_y=c_start_y
                for i,leg in enumerate(parlay_legs):
                    if i>0: draw.line([(40,curr_y),(width-40,curr_y)],(100,100,100),1); curr_y+=20
                    leg_lg=leg.get('league',eff_league); next_y=self._draw_parlay_leg_internal(img,draw,leg,leg_lg,width,curr_y,is_same_game,leg_h); draw=ImageDraw.Draw(img); curr_y=next_y
                tot_y=curr_y; draw.line([(40,tot_y),(width-40,tot_y)],'white',2); tot_y+=30
                tot_odds_txt=f"Total Odds: {self._format_odds_with_sign(odds)}"; draw.text((width//2,tot_y),tot_odds_txt,'white',self.font_b_28,'mm'); tot_y+=40
                units_txt=f"Stake: {units:.2f} Units"; bbox=draw.textbbox((0,0),units_txt,self.font_b_24); u_w=bbox[2]-bbox[0]
                lock=self._load_lock_icon()
                if lock:
                    sp=15; t_w=u_w+2*lock.width+2*sp; sx=(width-t_w)//2
                    if img.mode!='RGBA': img=img.convert("RGBA"); tmp=Image.new('RGBA',img.size,(0,0,0,0)); tmp.paste(lock,(sx,int(tot_y-lock.height/2)),lock); img=Image.alpha_composite(img,tmp); draw=ImageDraw.Draw(img)
                    tx=sx+lock.width+sp; draw.text((tx+u_w/2,tot_y),units_txt,(255,215,0),self.font_b_24,'mm')
                    tmp=Image.new('RGBA',img.size,(0,0,0,0)); tmp.paste(lock,(int(tx+u_w+sp),int(tot_y-lock.height/2)),lock); img=Image.alpha_composite(img,tmp); draw=ImageDraw.Draw(img)
                else: draw.text((width//2,tot_y),f"🔒 {units_txt} 🔒",(255,215,0),self.emoji_font_24,'mm')
            else: draw.text((width//2,height//2),"Invalid Bet Data",'red',self.font_b_36,'mm')
            # Footer
            f_y=height-footer_h//2; id_txt=f"Bet #{bet_id}"; ts_txt=timestamp.strftime('%Y-%m-%d %H:%M UTC')
            draw.text((self.padding,f_y),id_txt,(150,150,150),self.font_m_18,'lm'); draw.text((width-self.padding,f_y),ts_txt,(150,150,150),self.font_m_18,'rm')
            logger.info(f"Bet slip generated OK: {bet_id}"); return img.convert("RGB")
        except Exception as e:
            logger.exception(f"Error generating bet slip {bet_id}: {e}")
            err_img=Image.new('RGB',(800,200),(40,40,40)); draw=ImageDraw.Draw(err_img); font=self.font_m_24
            draw.text((400,100),"Error Generating Slip",'red',font,"mm"); return err_img

    def _draw_parlay_leg_internal(
        self, image: Image.Image, draw: ImageDraw.Draw, leg: Dict[str, Any], league: Optional[str],
        width: int, start_y: int, is_same_game: bool, leg_height: int
    ) -> int:
        leg_home=leg.get('home_team',leg.get('team','Unk')); leg_away=leg.get('opponent','Unk')
        leg_line=leg.get('line','N/A'); leg_odds=leg.get('odds',0); leg_lg=leg.get('league',league or 'UNK')
        logo_y=start_y+10; l_sz=(50,50); txt_x=40; team_logo=None
        team_show=leg.get('team',leg_home)
        if team_show!='Unknown': team_logo=self._load_team_logo(team_show,leg_lg)
        if team_logo:
            lx=40; disp=team_logo.resize(l_sz,Image.Resampling.LANCZOS);
            if image.mode!='RGBA': image=image.convert("RGBA"); tmp=Image.new('RGBA',image.size,(0,0,0,0)); tmp.paste(disp,(lx,logo_y),disp); image=Image.alpha_composite(image,tmp); draw=ImageDraw.Draw(image); txt_x=lx+l_sz[0]+15
        draw.text((txt_x,logo_y+5),leg_line,'white',self.font_m_24)
        h=leg.get('home_team',leg_home); a=leg.get('opponent',leg_away); parts=[]
        if h!='Unknown': parts.append(h)
        if a!='Unknown' and a!=h: parts.append(f"vs {a}")
        matchup=" ".join(parts) if parts else team_show
        draw.text((txt_x,logo_y+40),f"{leg_lg} - {matchup}",(180,180,180),self.font_m_18)
        odds_txt=self._format_odds_with_sign(leg_odds); bbox=draw.textbbox((0,0),odds_txt,self.font_b_28)
        tw=bbox[2]-bbox[0]; th=bbox[3]-bbox[1]; odds_y=start_y+(leg_height/2)-(th/2)
        draw.text((width-40-tw,int(odds_y)),odds_txt,'white',self.font_b_28)
        return start_y+leg_height
