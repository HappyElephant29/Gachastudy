import customtkinter as ctk
import pygame 
import random 
import os
import json 
from PIL import Image, ImageDraw, ImageTk
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

KEEPSAKES = {
    "Common": ["Frigo Camello", "Balerinna Cappucinna", "Brr Brr Patapim"],
    "Rare": ["Lirili Larila", "Chimpanzini Bananini"],
    "Epic": ["Bombardino Crocodilo", "Assasino Cappuccino"],
    "Legendary": ["Tralalero Tralala"],
    "Mythic": ["Tung Tung Tung Sahur"]
}

CONSUMABLES = {
    "Common": ["50 Bonus Coins", "Instant 25 Coins", "+50% Coins (Next Session)"],
    "Rare": ["Double Coin Gain (2 hours)", "Gamble 100 Coins"],
    "Epic": ["Modified Loot Box Rate", "Instant 300 Coins"],
    "Legendary": ["Next Box Guaranteed Keepsake", "Gain 5 Random Consumables"],
    "Mythic": ["Gain 100 Loot Boxes!"]
}

BUFF_ITEMS = ["50 Bonus Coins", "+50% Coins (Next Session)", "Double Coin Gain (2 hours)", "Modified Loot Box Rate"]

ITEM_DESCRIPTIONS = {

    "Frigo Camello": "Normal coin gain rate increases by 5/5.5/6/6.5/7%.",
    "Balerinna Cappucinna": "Gain 10/12.5/15/17.5 / 20% more coins for the first 30 mins.",
    "Brr Brr Patapim": "Gain 15/20/25/30/35 coins after a session ends (min 15 mins).",
    "Lirili Larila": "Starts at -20% gain, increases by 6/7/8/9/10% every 15 mins.",
    "Chimpanzini Bananini": "Interest-based gain: 5/6/7/8/9% of savings every 30m. Normal gain disabled.",
    "Bombardino Crocodilo": "Long sessions guarantee a Keepsake in the next box.",
    "Assasino Cappuccino": "Burst: After 2/2.25/2.5/2.75/3 hours, gain 2x coins for 1 hour.",
    "Tralalero Tralala": "Find a random consumable every 2/2.25/2.5/2.75/3 hours.",
    "Tung tung tung saham": "MYTHIC: Every 20 mins counts as 30 mins for all other keepsakes.",
    "50 Bonus Coins": "Extra 50 coins after 30 mins of studying.",
    "Instant 25 Coins": "Instantly adds 25 coins.",
    "+50% Coins (Next Session)": "+50% gain rate for the duration of one session.",
    "Double Coin Gain (2 hours)": "2x gain rate for the next 2 hours of study.",
    "Gamble 100 Coins": "60% chance to win 200, 40% to lose 100.",
    "Modified Loot Box Rate": "Improves luck for the next session.",
    "Instant 300 Coins": "Instantly adds 300 coins.",
    "Next Box Guaranteed Keepsake": "Next lootbox will not contain a consumable.",
    "Gain 5 Random Consumables": "Adds 5 random consumables to inventory.",
    "Gain 100 Loot Boxes!": "MYTHIC: Massive unboxing session!"
}

REFUNDS = {"Common": 50, "Rare": 100, "Epic": 300, "Legendary": 1000}
RARITY_COLORS = {"Common": "#ADB5BD", "Rare": "#339AF0", "Epic": "#CC5DE8", "Legendary": "#FF922B", "Mythic": "#FA5252"}

# =============================================================================
# MAIN APPLICATION CLASS
# =============================================================================
class StudyQuestTimer:
    def __init__(self):
        pygame.mixer.init()

        # --- Player State ---
        self.coins = 100.0  
        self.base_coins_per_hour = 200.0 
        self.passive_rate_multiplier = 1.0 
        self.current_coins_per_minute = self.base_coins_per_hour / 60.0
        self.used_codes = [] # Track redeemed codes

        # --- Progression ---
        self.boxes_opened = 0
        self.pity_counter = 0
        self.total_study_seconds = 0
        self.session_study_seconds = 0 
        self.keepsakes_inventory = {} 
        self.consumables_inventory = {} 
        self.keepsake_study_time = {} 
        
        # --- Buffs & Flags ---
        self.active_session_buffs = [] 
        self.guaranteed_keepsake_flag = False
        self.keepsake_slots = 1 
        self.equipped_keepsakes = [None] 

        # --- Timer UI ---
        self.time_left = 1500 
        self.is_expanded = False
        self.is_running = False

        self.root = ctk.CTk()
        
        try:
            img_path = resource_path(os.path.join("Sprites", "Assassino.png"))
            img = Image.open(img_path)
            # This works for the dock icon and window top-left
            self.root.iconphoto(False, ImageTk.PhotoImage(img))
        except Exception as e:
            print(f"Icon error: {e}")
        self.root.title("Study Gacha")
        self.root.geometry("280x200")
        self.root.attributes("-topmost", True) 
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.image_cache = {} 
        self.load_data()
        self.build_ui()
        self.recalculate_passive_stats() 
        self.update_display()
        #self.unlock_all_cheat()

    # -------------------------------------------------------------------------
    # DATA MANAGEMENT
    # -------------------------------------------------------------------------
    def load_data(self):
        try:
            with open("save_data.json", "r") as f:
                d = json.load(f)
                self.coins = d.get("coins", 100.0)
                self.boxes_opened = d.get("boxes_opened", 0)
                self.total_study_seconds = d.get("total_study_seconds", 0)
                self.keepsakes_inventory = d.get("keepsakes_inventory", {})
                self.consumables_inventory = d.get("consumables_inventory", {})
                self.keepsake_slots = d.get("keepsake_slots", 1)
                self.equipped_keepsakes = d.get("equipped_keepsakes", [None])
                self.keepsake_study_time = d.get("keepsake_study_time", {})
                self.used_codes = d.get("used_codes", [])
        except: pass

    def save_data(self):
        d = {
            "coins": self.coins, "boxes_opened": self.boxes_opened,
            "total_study_seconds": self.total_study_seconds,
            "keepsakes_inventory": self.keepsakes_inventory,
            "consumables_inventory": self.consumables_inventory,
            "keepsake_slots": self.keepsake_slots,
            "equipped_keepsakes": self.equipped_keepsakes,
            "keepsake_study_time": self.keepsake_study_time,
            "used_codes": self.used_codes
        }
        with open("save_data.json", "w") as f:
            json.dump(d, f, indent=4) 

    def on_closing(self):
            """Forcefully shuts down the app and all background engines."""
            # 1. Save data first so no progress is lost[cite: 5]
            self.save_data() 
            
            # 2. Stop the pygame engines
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                pygame.quit()
            except:
                pass

            # 3. Terminate the mainloop and window
            self.root.quit()    # Stops the internal mainloop
            self.root.destroy() # Closes the window
            os._exit(0)

    def reset_data(self):
        self.coins = 100.0; self.boxes_opened = 0; self.total_study_seconds = 0
        self.keepsakes_inventory = {}; self.consumables_inventory = {}
        self.equipped_keepsakes = [None]; self.keepsake_study_time = {}
        self.save_data(); self.recalculate_passive_stats()
        self.update_coin_display(); self.render_hub_equipment()

    # -------------------------------------------------------------------------
    # IMAGE & UI RENDER
    # -------------------------------------------------------------------------
    def load_item_image(self, name, size=(40, 40)):
            cache_key = f"{name}_{size[0]}"
            if cache_key in self.image_cache: 
                return self.image_cache[cache_key]
                
            path = resource_path(os.path.join("Sprites", f"{name}.png"))
            try:
                # 1. Open the original 32x32 image
                img = Image.open(path)
                
                # 2. Manually resize it using NEAREST before it hits the UI
                # This is the "Gold Standard" fix for pixel art resolution
                img_resized = img.resize(size, Image.Resampling.NEAREST)
                
                # 3. Create the CTKImage with the already-resized sharp image
                ctk_img = ctk.CTkImage(light_image=img_resized, 
                                    dark_image=img_resized, 
                                    size=size)
                
                self.image_cache[cache_key] = ctk_img
                return ctk_img
            except:
                img = Image.new("RGBA", size, (80, 80, 80, 255))
                return ctk.CTkImage(light_image=img, dark_image=img, size=size)
            
    def build_ui(self):
        # Timer Entry
        top = ctk.CTkFrame(self.root, fg_color="transparent"); top.pack(pady=(15, 5))
        self.time_entry = ctk.CTkEntry(top, width=60, justify="center"); self.time_entry.pack(side="left", padx=5)
        self.time_entry.insert(0, "25")
        self.set_btn = ctk.CTkButton(top, text="Set", width=50, command=self.set_custom_time); self.set_btn.pack(side="left")

        self.msg_label = ctk.CTkLabel(self.root, text="", font=("Helvetica", 12)); self.msg_label.pack()
        self.timer_label = ctk.CTkLabel(self.root, text="25:00", font=("Helvetica", 48, "bold")); self.timer_label.pack(pady=(0, 10))

        # Controls
        ctrl = ctk.CTkFrame(self.root, fg_color="transparent"); ctrl.pack()
        self.start_btn = ctk.CTkButton(ctrl, text="▶ Start", width=100, fg_color="#2B8A3E", command=self.toggle_timer); self.start_btn.grid(row=0, column=0, padx=5)
        self.expand_btn = ctk.CTkButton(ctrl, text="🔼 Hub", width=100, command=self.toggle_menu); self.expand_btn.grid(row=0, column=1, padx=5)

        # Hub
        self.hub_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.coin_label = ctk.CTkLabel(self.hub_frame, text=f"Coins: {int(self.coins)}", font=("Helvetica", 18, "bold"), text_color="#F9A826"); self.coin_label.pack(pady=(10, 0))
        self.rate_label = ctk.CTkLabel(self.hub_frame, text="Rate: 0.00 / min", font=("Helvetica", 12)); self.rate_label.pack(pady=(0, 5))

        self.equip_frame = ctk.CTkFrame(self.hub_frame, fg_color="#2B2D31", corner_radius=10); self.equip_frame.pack(pady=5, padx=10, fill="x")
        self.equip_slots_frame = ctk.CTkFrame(self.equip_frame, fg_color="transparent"); self.equip_slots_frame.pack(pady=5)
        self.render_hub_equipment()

        self.loot_btn = ctk.CTkButton(self.hub_frame, text="Open Lootbox (100 coins)", width=200, fg_color="#7950F2", command=self.open_lootbox); self.loot_btn.pack(pady=5)
        self.inv_btn = ctk.CTkButton(self.hub_frame, text="Inventory", width=200, fg_color="#495057", command=self.show_inventory); self.inv_btn.pack(pady=5)
        self.settings_btn = ctk.CTkButton(self.hub_frame, text="⚙️ Settings", width=200, command=self.show_settings); self.settings_btn.pack(pady=5)
        self.loot_result = ctk.CTkLabel(self.hub_frame, text="", font=("Helvetica", 12)); self.loot_result.pack()

    def set_hub_state(self, state):
        self.loot_btn.configure(state=state); self.inv_btn.configure(state=state); self.settings_btn.configure(state=state)
        self.set_btn.configure(state=state); self.time_entry.configure(state=state)
        for w in self.equip_slots_frame.winfo_children():
            if isinstance(w, ctk.CTkButton): w.configure(state=state)

    def render_hub_equipment(self):
        st = "disabled" if self.is_running else "normal"
        for w in self.equip_slots_frame.winfo_children(): w.destroy()
        
        # 1. Calculate Standard Slots (Unlock at 2 hours)
        base_slots = 2 if self.total_study_seconds >= 7200 else 1
        
        # 2. Total slots is always Base + 1 (The Dedicated Mythic Slot)
        self.keepsake_slots = base_slots + 1
        
        # Ensure the list is long enough to hold all items
        while len(self.equipped_keepsakes) < self.keepsake_slots:
            self.equipped_keepsakes.append(None)

        for i in range(self.keepsake_slots):
            it = self.equipped_keepsakes[i]
            is_mythic_slot = (i == self.keepsake_slots - 1)
            
            # --- FIX: Avoid "transparent" for border_color ---
            bg = "#5c1d1d" if is_mythic_slot else "#343A40"
            
            # If it's mythic, use the red border. 
            # If not mythic, use the button's own background color as the border 
            # (this makes it invisible without using the forbidden "transparent" keyword).
            current_border = "#FA5252" if is_mythic_slot else bg 
            
            if it:
                img = self.load_item_image(it)
                ctk.CTkButton(self.equip_slots_frame, 
                              image=img, 
                              text="", 
                              width=40, 
                              height=40, 
                              fg_color="transparent", 
                              border_width=2 if is_mythic_slot else 0,
                              border_color=current_border, # Corrected color
                              command=lambda idx=i: self.unequip_item(idx), 
                              state=st).pack(side="left", padx=5)
            else:
                label = "M" if is_mythic_slot else "+"
                ctk.CTkButton(self.equip_slots_frame, 
                              text=label, 
                              width=40, 
                              height=40, 
                              fg_color=bg, 
                              text_color="#FA5252" if is_mythic_slot else "white",
                              border_width=2 if is_mythic_slot else 0,
                              border_color=current_border, # Corrected color
                              state=st).pack(side="left", padx=5)
        
        if base_slots < 2:
            remaining_h = max(0, 2 - (self.total_study_seconds // 3600))
            ctk.CTkLabel(self.equip_slots_frame, text=f"Next slot: {remaining_h}h left", 
                         font=("Helvetica", 10, "italic"), text_color="#ADB5BD").pack(side="left", padx=10)
    # -------------------------------------------------------------------------
    # STAT ENGINE & TIMER
    # -------------------------------------------------------------------------
    def recalculate_passive_stats(self):
        self.passive_rate_multiplier = 1.0 
        for it in self.equipped_keepsakes:
            if it == "Frigo Camello":
                self.passive_rate_multiplier += [0.05, 0.055, 0.06, 0.065, 0.07][self.keepsakes_inventory.get(it, 1)-1]
        if not self.is_running:
            self.current_coins_per_minute = (self.base_coins_per_hour * self.passive_rate_multiplier) / 60.0
            self.update_coin_display()

    def toggle_timer(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.start_btn.configure(text="⏸ Pause", fg_color="#E03131"); self.set_hub_state("disabled"); self.tick_timer()
        else:
            self.start_btn.configure(text="▶ Start", fg_color="#2B8A3E"); self.set_hub_state("normal")

    def tick_timer(self):
            if self.is_running and self.time_left > 0:
                self.time_left -= 1
                self.total_study_seconds += 1
                self.session_study_seconds += 1
                
                # --- Check for Slot Unlock (7,200 seconds = 2 Hours) ---
                if self.total_study_seconds == 7200:
                    self.keepsake_slots = 2
                    self.equipped_keepsakes.append(None)
                    self.render_hub_equipment()
                    self.msg_label.configure(text="NEW SLOT UNLOCKED!", text_color="#51CF66")

                # --- Mythic Time Acceleration (Tung Tung Tung Sahur) ---
                log_sec = self.session_study_seconds
                if self.keepsakes_inventory.get("Tung Tung Tung saham", 0) > 0:
                    log_sec = int(self.session_study_seconds * 1.5)
        
                for it in self.equipped_keepsakes:
                    if it: self.keepsake_study_time[it] = self.keepsake_study_time.get(it, 0) + 1
                
                mult = self.passive_rate_multiplier
                
                # --- Keepsake Logic ---
                for it in self.equipped_keepsakes:
                    if not it: continue
                    lv = self.keepsakes_inventory.get(it, 1)
                    if it == "Balerinna Cappucinna" and log_sec <= 1800: mult += [0.1, 0.125, 0.15, 0.175, 0.2][lv-1]
                    if it == "Bombardino Crocodilo" and log_sec >= 7200:
                        if not self.guaranteed_keepsake_flag:
                            self.guaranteed_keepsake_flag = True
                            self.msg_label.configure(text="CROCODILE PRIDE: Next box is a Keepsake!", text_color="#CC5DE8")
                    if it == "Lirili Larila": mult += (-0.20 + ((log_sec // 900) * [0.06, 0.07, 0.08, 0.09, 0.10][lv-1]))
                    if it == "Chimpanzini Bananini":
                        mult = 0
                        if log_sec % 1800 == 0: self.coins += (self.coins * [0.05, 0.06, 0.07, 0.08, 0.09][lv-1])
                    if it == "Assasino Cappuccino":
                        thresh = [10800, 9900, 9000, 8100, 7200][lv-1]
                        if thresh <= log_sec <= thresh + 3600: mult += [0.6, 0.7, 0.8, 0.9, 1.0][lv-1]
                    if it == "Tralalero Tralala" and log_sec % [10800, 9900, 9000, 8100, 7200][lv-1] == 0:
                        c = random.choice(CONSUMABLES[self.roll_rarity()])
                        self.consumables_inventory[c] = self.consumables_inventory.get(c, 0) + 1

                # --- Consumable Buffs (Active Check) ---
                if "Double Coin Gain (2 hours)" in self.active_session_buffs and self.session_study_seconds <= 7200: 
                    mult *= 2
                if "+50% Coins (Next Session)" in self.active_session_buffs: 
                    mult += 0.5
                if "50 Bonus Coins" in self.active_session_buffs and log_sec == 1800: 
                    self.coins += 50

                self.current_coins_per_minute = (self.base_coins_per_hour * mult) / 60.0
                self.coins += (self.current_coins_per_minute / 60.0)
                self.update_display()
                
                if self.time_left % 5 == 0: self.update_coin_display()
                self.root.after(1000, self.tick_timer)

            elif self.time_left == 0:
                # --- SESSION COMPLETE ---
                # 1. Handle End-of-Session Keepsake Rewards
                if "Brr Brr Patapim" in self.equipped_keepsakes and self.session_study_seconds >= 900:
                    self.coins += [15, 20, 25, 30, 35][self.keepsakes_inventory["Brr Brr Patapim"]-1]
                
                # 2. CONSUME ACTIVE BUFFS: Remove them from inventory now that they are finished
                for buff in self.active_session_buffs:
                    if buff in self.consumables_inventory and self.consumables_inventory[buff] > 0:
                        self.consumables_inventory[buff] -= 1
                
                # 3. Reset State
                self.is_running = False
                self.active_session_buffs = [] # This un-highlights the items in inventory
                self.set_hub_state("normal")
                self.save_data()
                self.update_coin_display()

    # -------------------------------------------------------------------------
    # LOOT & INVENTORY
    # -------------------------------------------------------------------------

    def roll_rarity(self):
        """Calculates loot rarity with a hard pity at 25 rolls."""
        # Ensure pity_counter exists; initialize if it doesn't to avoid further errors
        if not hasattr(self, 'pity_counter'):
            self.pity_counter = 0
            
        self.pity_counter += 1
        is_lucky = "Modified Loot Box Rate" in self.active_session_buffs
        
        # --- PITY TRIGGER ---
        if self.pity_counter >= 25:
            self.pity_counter = 0 
            roll = random.uniform(90, 100)
        else:
            roll = random.uniform(0, 100)

        # Standard Rarity Logic
        if is_lucky:
            if roll <= 40: res = "Common"
            elif roll <= 75: res = "Rare"
            elif roll <= 92: res = "Epic"
            elif roll <= 99.5: res = "Legendary"
            else: res = "Mythic"
        else:
            if roll <= 60: res = "Common"
            elif roll <= 90: res = "Rare"
            elif roll <= 98: res = "Epic"
            elif roll <= 99.9: res = "Legendary"
            else: res = "Mythic"

        if res in ["Epic", "Legendary", "Mythic"]:
            self.pity_counter = 0
            
        return res

    def open_lootbox(self):
        """Entry point for the lootbox button."""
        if self.coins < 100:
            self.loot_result.configure(text="Not enough coins!", text_color="#FA5252")
            return
        
        self.coins -= 100
        self.boxes_opened += 1
        self.update_coin_display()
        
        self.loot_btn.configure(state="disabled")
        self.animate_shake(15) # This is the method that was missing

    def animate_shake(self, count):
        """The jitter animation method."""
        if count > 0:
            frames = ["--- OPENING ---", ">>> OPENING <<<", "=== OPENING ==="]
            colors = ["#ADB5BD", "#FFFFFF", "#F9A826"]
            self.loot_result.configure(text=random.choice(frames), text_color=random.choice(colors))
            
            wait_time = 40 + (count * 2) 
            self.root.after(wait_time, lambda: self.animate_shake(count - 1))
        else:
            self.reveal_item()

    def reveal_item(self):
            rarity = self.roll_rarity()
            is_keepsake = random.random() < 0.2 or self.boxes_opened == 1 or self.guaranteed_keepsake_flag
            
            color = RARITY_COLORS[rarity]

            try:
                path = resource_path(os.path.join("Audios", "CoinSound.mp3"))
                if os.path.exists(path):
                    # Use mixer.Sound for quick SFX so it doesn't 
                    # interrupt the music.load in reveal_item
                    sfx = pygame.mixer.Sound(path)
                    sfx.set_volume(0.8)
                    sfx.play()
            except Exception as e:
                print("No Audio Found")
            
            if is_keepsake:
                item_name = random.choice(KEEPSAKES[rarity])
                self.guaranteed_keepsake_flag = False
                result_text = self.handle_keepsake_drop(item_name, rarity)
                # Trigger sound for keepsakes
                self.play_item_sound(item_name)
            else:
                item_name = random.choice(CONSUMABLES[rarity])
                result_text = self.handle_consumable_drop(item_name, rarity)

            # 1. Update the visual result label
            self.loot_result.configure(text=result_text.upper(), text_color="white", fg_color=color)
            
            # 2. Reset the label background after a short delay
            self.root.after(300, lambda: self.loot_result.configure(fg_color="transparent", text_color=color))
            
            # 3. CRITICAL FIX: Re-enable the loot button here!
            # This ensures the button unlocks every time, even for consumables.
            self.loot_btn.configure(state="normal") 
            
            self.save_data()
    # -------------------------------------------------------------------------
    # DROP HANDLERS
    # -------------------------------------------------------------------------
    def handle_keepsake_drop(self, item_name, rarity):
        if item_name not in self.keepsakes_inventory:
            self.keepsakes_inventory[item_name] = 1
            return f"★ NEW ★\n{item_name}"
        else:
            if self.keepsakes_inventory[item_name] < 5:
                self.keepsakes_inventory[item_name] += 1
                return f"UPGRADE!\n{item_name} LV.{self.keepsakes_inventory[item_name]}"
            else:
                refund = REFUNDS.get(rarity, 50)
                self.coins += refund
                return f"MAXED!\n+{refund} COINS"

    def handle_consumable_drop(self, item_name, rarity):
        self.consumables_inventory[item_name] = self.consumables_inventory.get(item_name, 0) + 1
        return f"[{rarity}]\n{item_name}"

        # 3. Cinematic 'Impact'
        # Set the result text to uppercase and add symbols based on rarity
        current_text = self.loot_result.cget("text")
        flash_prefix = "★ " if rarity in ["Legendary", "Mythic"] else ""
        self.loot_result.configure(text=f"{flash_prefix}{current_text.upper()} {flash_prefix}")
        
        # Re-enable the button
        self.loot_btn.configure(state="normal")
        self.save_data()

    def show_inventory(self):
        win = ctk.CTkToplevel(self.root)
        win.title("Inventory")
        win.geometry("360x600") 
        win.attributes("-topmost", True)

        sc = ctk.CTkScrollableFrame(win, width=320, height=300)
        sc.pack(padx=10, pady=10, fill="both", expand=True)

        # Make Images More Clear
        inf = ctk.CTkFrame(win, height=350, fg_color="#2B2D31") # Increased from 220
        inf.pack(padx=10, pady=10, fill="x", side="bottom")
        inf.pack_propagate(False)

        self.preview_icon = ctk.CTkLabel(inf, text="", width=50, height=50)
        self.preview_icon.pack(pady=10)

        tl = ctk.CTkLabel(inf, text="Select an Item", font=("Helvetica", 16, "bold"))
        tl.pack()
        
        lbl = ctk.CTkLabel(inf, text="", wraplength=300)
        lbl.pack()

        btn = ctk.CTkButton(inf, text="Action", width=100)
        btn.pack_forget()

        def click(n, cat):
            tl.configure(text=n)
            d = ITEM_DESCRIPTIONS.get(n, "")
            
            large_img = self.load_item_image(n, size=(100, 100))
            self.preview_icon.configure(image=large_img)

            if cat == "K":
                u = self.keepsake_study_time.get(n, 0)
                extra_note = "\n[SPECIAL MYTHIC SLOT]" if n == "Tung Tung Tung Sahur" else ""
                lbl.configure(text=f"{d}{extra_note}\n\nTime Used: {u//3600}h {(u%3600)//60}m")
                btn.configure(text="Equip to Mythic Slot" if n == "Tung Tung Tung Sahur" else "Equip Keepsake", 
                              command=lambda: [self.equip_item(n), win.destroy()])
                btn.pack(pady=10)
            else:
                lbl.configure(text=d)
                is_disabled = n in BUFF_ITEMS and len(self.active_session_buffs) > 0
                btn.configure(text="Use Consumable", state="disabled" if is_disabled else "normal", 
                              command=lambda: [self.use_consumable(n), win.destroy()])
                btn.pack(pady=10)

        # Categorize items 
        for label, items, code in [("KEEPSAKES", self.keepsakes_inventory, "K"), 
                                   ("CONSUMABLES", self.consumables_inventory, "C")]:
            ctk.CTkLabel(sc, text=label, font=("Helvetica", 16, "bold")).pack(pady=5)
            for k, v in items.items():
                if v <= 0: continue
                r = ctk.CTkFrame(sc, fg_color="transparent")
                r.pack(fill="x", pady=2)
                
                # Check if this specific consumable is currently active
                is_active = (k in self.active_session_buffs)
                
                # Set the color: Green if active, transparent if not
                bg_color = "#2F855A" if is_active else "transparent"
                btn_text = f"{k} (ACTIVE)" if is_active else f"{k} ({v})"

                ctk.CTkButton(r, text=btn_text, 
                            fg_color=bg_color, 
                            anchor="w",
                            state="disabled" if is_active else "normal",
                            command=lambda n=k, t=code: click(n, t)).pack(side="left", fill="x", expand=True)

    def equip_item(self, n):
        """Logic to handle standard slots and the dedicated Mythic slot."""
        mythic_idx = self.keepsake_slots - 1
        
        # 1. Logic for the Mythic Item
        if n == "Tung Tung Tung Sahur":
            if self.equipped_keepsakes[mythic_idx] is None:
                self.equipped_keepsakes[mythic_idx] = n
                self.recalculate_passive_stats()
                self.render_hub_equipment()
                self.save_data()
                return
            else:
                self.msg_label.configure(text="Mythic slot is full!", text_color="#FA5252")
                return
        
        # 2. Logic for all other Keepsakes (Standard Slots)
        else:
            # We only look at slots before the Mythic index
            for i in range(mythic_idx):
                if self.equipped_keepsakes[i] is None:
                    self.equipped_keepsakes[i] = n
                    self.recalculate_passive_stats()
                    self.render_hub_equipment()
                    self.save_data()
                    return
            
            self.msg_label.configure(text="No standard slots available!", text_color="#FA5252")

    def unequip_item(self, idx):
        """Clears a slot and updates stats."""
        if idx < len(self.equipped_keepsakes):
            self.equipped_keepsakes[idx] = None
            self.recalculate_passive_stats()
            self.render_hub_equipment()
            self.save_data()
                
    def use_consumable(self, n):
        if self.consumables_inventory.get(n, 0) <= 0: return
        
        # 1. If it's a BUFF item (Duration based), add it to active list
        if n in BUFF_ITEMS:
            if n not in self.active_session_buffs:
                self.active_session_buffs.append(n)
            else:
                self.msg_label.configure(text="Buff already active!", text_color="#ADB5BD")
                return
        
        # 2. If it's an INSTANT item, apply it and remove it immediately
        elif n == "Instant 25 Coins": 
            self.coins += 25
            self.consumables_inventory[n] -= 1
        elif n == "Instant 300 Coins": 
            self.coins += 300
            self.consumables_inventory[n] -= 1
        elif n == "Gamble 100 Coins": 
            self.coins -= 100
            if random.random() < 0.6: self.coins += 200
            self.consumables_inventory[n] -= 1
        elif n == "Gain 100 Loot Boxes!":
            self.coins += 10000 
            self.consumables_inventory[n] -= 1
        elif n == "Gain 5 Random Consumables":
            for _ in range(5): 
                it = random.choice(CONSUMABLES[self.roll_rarity()])
                self.consumables_inventory[it] = self.consumables_inventory.get(it, 0) + 1
            self.consumables_inventory[n] -= 1
        elif n == "Next Box Guaranteed Keepsake": 
            self.guaranteed_keepsake_flag = True
            self.consumables_inventory[n] -= 1

        self.update_coin_display()
        self.save_data()
    # -------------------------------------------------------------------------
    # AUDIOS
    # -------------------------------------------------------------------------

    def play_item_sound(self, name):
            """Plays the mp3 and sets a timer to stop it."""
            path = resource_path(os.path.join("Audios", f"{name}.mp3"))
            
            if os.path.exists(path):
                try:
                    pygame.mixer.music.set_volume(0.8)
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.play()
                    
                    self.root.after(10000, pygame.mixer.music.stop) 
                except Exception as e:
                    print(f"Audio Error: {e}")

    # -------------------------------------------------------------------------
    # AUDIOS
    # -------------------------------------------------------------------------

    def redeem_code(self, code_entry):
        """Checks the gift code, grants 200 coins, and marks as used."""
        code = code_entry.get().strip().upper()
        valid_codes = ["ILOVEGAMBLING"]
        
        if code in self.used_codes:
            self.msg_label.configure(text="Code already redeemed!", text_color="#ADB5BD")
        elif code in valid_codes:
            self.used_codes.append(code) # Mark as used
            self.coins += 200.0
            self.update_coin_display()
            self.save_data()
            
            # Display Success message
            self.msg_label.configure(text="SUCCESS! +200 Coins", text_color="#51CF66")
            code_entry.delete(0, 'end')
        else:
            self.msg_label.configure(text="Invalid Code!", text_color="#FA5252")

    # -------------------------------------------------------------------------
    # UTILS
    # -------------------------------------------------------------------------
    def update_coin_display(self):
        self.coin_label.configure(text=f"Coins: {int(self.coins)}")
        self.rate_label.configure(text=f"Rate: {self.current_coins_per_minute:.2f} / min")

    def set_custom_time(self):
        try: self.time_left = int(self.time_entry.get()) * 60; self.session_study_seconds = 0; self.update_display()
        except: pass

    def update_display(self):
        m, s = divmod(self.time_left, 60); self.timer_label.configure(text=f"{m:02d}:{s:02d}")

    def toggle_menu(self):
        if self.is_expanded: self.root.geometry("280x200"); self.hub_frame.pack_forget()
        else: self.root.geometry("300x540"); self.hub_frame.pack(fill="both", expand=True, padx=15, pady=15)
        self.is_expanded = not self.is_expanded


    def unlock_all_cheat(self):
        """Developer tool to unlock all items and massive coins."""
        self.coins += 1000000.0
        
        # Unlock all Keepsakes at Level 1
        for rarity in KEEPSAKES:
            for item in KEEPSAKES[rarity]:
                if item not in self.keepsakes_inventory:
                    self.keepsakes_inventory[item] = 1
        
        # Unlock 10 of every Consumable
        for rarity in CONSUMABLES:
            for item in CONSUMABLES[rarity]:
                self.consumables_inventory[item] = self.consumables_inventory.get(item, 0) + 10
        
        self.update_coin_display()
        self.save_data()
        self.msg_label.configure(text="CHEAT ENABLED: Everything Unlocked!", text_color="#FA5252")
            
    def show_settings(self):
        """Displays a polished Stats and Reset interface."""
        settings_win = ctk.CTkToplevel(self.root)
        settings_win.title("Settings & Stats")
        settings_win.geometry("300x420")
        settings_win.attributes("-topmost", True)

        # Header
        ctk.CTkLabel(settings_win, text="📊 Player Stats", font=("Helvetica", 20, "bold"), text_color="#F9A826").pack(pady=(20, 10))

        # Stats Container
        stat_frame = ctk.CTkFrame(settings_win, fg_color="#2B2D31", corner_radius=12)
        stat_frame.pack(padx=20, fill="x", pady=10)

        # Calculate Detailed Time
        total_h, remainder = divmod(self.total_study_seconds, 3600)
        total_m, _ = divmod(remainder, 60)
        
        # Display Stats
        ctk.CTkLabel(stat_frame, text="Lifetime Study Time:", font=("Helvetica", 12), text_color="#ADB5BD").pack(pady=(10, 0))
        ctk.CTkLabel(stat_frame, text=f"{total_h} Hours, {total_m} Mins", font=("Helvetica", 18, "bold"), text_color="#51CF66").pack(pady=(0, 10))

        ctk.CTkLabel(stat_frame, text="Total Lootboxes Opened:", font=("Helvetica", 12), text_color="#ADB5BD").pack(pady=(5, 0))
        ctk.CTkLabel(stat_frame, text=f"{self.boxes_opened}", font=("Helvetica", 18, "bold"), text_color="#339AF0").pack(pady=(0, 15))

        # --- Gift Code Section ---
        ctk.CTkLabel(settings_win, text="Gift Code", font=("Helvetica", 14, "bold")).pack(pady=(10, 0))
        
        code_frame = ctk.CTkFrame(settings_win, fg_color="transparent")
        code_frame.pack(pady=5)
        
        code_entry = ctk.CTkEntry(code_frame, placeholder_text="Enter Code...", width=150)
        code_entry.pack(side="left", padx=5)
        
        redeem_btn = ctk.CTkButton(code_frame, text="Redeem", width=80, 
                                   fg_color="#F9A826", hover_color="#E6951D", text_color="black",
                                   command=lambda: self.redeem_code(code_entry))
        redeem_btn.pack(side="left")

        self.reset_step = 0 # Tracks if user clicked once
        
        def attempt_reset():
            if self.reset_step == 0:
                reset_btn.configure(text="Confirm? (Click again to WIPE)", fg_color="#C92A2A")
                self.reset_step = 1
            else:
                self.reset_data()
                settings_win.destroy()

        reset_btn = ctk.CTkButton(settings_win, text="Reset All Data", 
                                  fg_color="#E03131", hover_color="#C92A2A", 
                                  height=35, font=("Helvetica", 13, "bold"),
                                  command=attempt_reset)
        reset_btn.pack(pady=5)

        ctk.CTkLabel(settings_win, text="This cannot be undone.", font=("Helvetica", 11, "italic"), text_color="#495057").pack()



if __name__ == "__main__":
    app = StudyQuestTimer(); app.root.mainloop()