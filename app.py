# app.py

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import json
from utils import *
from potentialEstimation import *
from squad_selection import organize_squads
from potentialEstimation import PERSONALITY_MAP
import traceback

DEBUG = False 

class SquadSelectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FM24 Tactical Squad Planner")
        self.root.geometry("1400x900")
        
        self.data = None
        self.weights = None
        self.role_position_map = None
        self.squad_role_score = None
        self.output_df = None
        
        self.default_tactic = [
            ("GK", "Sweeper Keeper (At)"),
            ("D, R", "Complete Wing-Back (Su)"),
            ("D, CR", "Central Defender (De)"),
            ("D, CL", "Central Defender (De)"),
            ("D, L", "Complete Wing-Back (At)"),
            ("DM, C", "Ball Winning Midfielder DM (De)"), 
            ("M, CR", "Advanced Playmaker CM (At)"), 
            ("M, CL", "Mezzala (Su)"),
            ("AM, R", "Winger (At)"),
            ("AM, L", "Inside Forward (Su)"),            
            ("ST, C", "Advanced Forward (At)")
        ]
        
        self.setup_main_layout()

    def setup_main_layout(self):
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True)
        self.setup_input_screen()

    def setup_input_screen(self):
        for widget in self.main_container.winfo_children(): widget.destroy()
        header = tk.Label(self.main_container, text="FM24 Squad Analyzer", font=("Arial", 18, "bold"))
        header.pack(pady=20)
        
        btn_frame = tk.Frame(self.main_container)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="1. Load HTML Squad File", command=self.load_data).pack(side="left", padx=10)
        self.tactic_btn = ttk.Button(btn_frame, text="2. Edit Tactic (Interactive Board)", command=self.open_tactic_editor, state="disabled")
        self.tactic_btn.pack(side="left", padx=10)
        self.run_btn = ttk.Button(btn_frame, text="3. Run Analysis", command=self.run_analysis, state="disabled")
        self.run_btn.pack(side="left", padx=10)
        
        self.tactic_display = tk.Label(self.main_container, text="Current Tactic: Default (awaiting configuration)", 
                                       font=("Arial", 11), fg="gray")
        self.tactic_display.pack(pady=10)

    def open_tactic_editor(self):
        editor_win = tk.Toplevel(self.root)
        editor = TacticalBoardEditor(editor_win, self.role_position_map, self.default_tactic)
        self.root.wait_window(editor_win)
        
        if editor.confirmed_tactic:
            self.default_tactic = editor.confirmed_tactic
            
            tactic_str = ", ".join([f"{pos}→{role.split('(')[0].strip()}" for pos, role in self.default_tactic[:5]])
            tactic_str += f" ... ({len(self.default_tactic)} total)"
            self.tactic_display.config(text=f"Current Tactic: {tactic_str}", fg="green")
            self.run_btn.config(state="normal")

    def load_data(self):
        file_path = filedialog.askopenfilename(filetypes=[("HTML files", "*.html")])
        if not file_path: return
        try:
            with open('attributes_weights.json', 'r') as f:
                weights_data = json.load(f)

            weights_df = pd.DataFrame(weights_data)

            # Build role-position map (FIXED)
            self.role_position_map = {}
            for entry in weights_data:
                role = entry.get("Roles")
                positions = entry.get("Positions", [])
                if role:
                    self.role_position_map[role] = positions

            if 'Roles' in weights_df.columns:
                weights_df.set_index('Roles', inplace=True)
                self.weights = weights_df.transpose()
            else:
                self.weights = weights_df

            self.tactic_btn.config(state="normal")
            
            raw_data = pd.read_html(file_path, header=0, encoding='utf-8', index_col=0)[0]
            
            if "UID" in raw_data.columns:
                raw_data['UID'] = raw_data['UID'].astype(str)

            raw_data.columns = raw_data.columns.str.strip()
            raw_data = raw_data.map(lambda x: x.strip() if isinstance(x, str) else x)

            raw_data['Position_List'] = raw_data['Position'].apply(parse_positions)

            self.squad_role_score = calculate_all_role_scores(raw_data, self.weights)

            if 'Personality' not in raw_data.columns:
                raw_data['Personality'] = 'Balanced'
            else:
                raw_data['Personality'] = raw_data['Personality'].fillna('Balanced')

            self.data = raw_data
            # debug_nan(self.data, "load_data")

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to load: {e}")

    def run_analysis(self):
        if self.data is None: return
        try:
            current_tactic = [[[part.strip() for part in pos.split(',')], role] 
                              for pos, role in self.default_tactic]
            potential_report = calculate_tactical_potential(
                self.data, 
                self.squad_role_score, 
                current_tactic
            )
            
            report_df = pd.concat([
                potential_report,
                self.data[['Position_List', 'Personality', 'Transfer Value', 'DoB']]
            ], axis=1)
            # debug_nan(report_df, "run_analysis")
            
            report_df['Value_Num'] = report_df['Transfer Value'].apply(parse_transfer_value)
            
            self.output_df = organize_squads(report_df, current_tactic, self.role_position_map)
            self.setup_results_screen(current_tactic)
            # debug_nan(report_df, "run_analysis")

        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", f"Analysis failed: {str(e)}")


    def setup_results_screen(self, current_tactic):
        for widget in self.main_container.winfo_children(): widget.destroy()
        
        action_bar = ttk.Frame(self.main_container)
        action_bar.pack(fill="x", padx=10, pady=5, side="top")
        ttk.Button(action_bar, text="⚽ Squad Board", command=lambda: self.show_squad_visualizer(current_tactic)).pack(side="left", padx=5)
        ttk.Button(action_bar, text="📥 Export CSV", command=self.export_results).pack(side="left", padx=5)
        ttk.Button(action_bar, text="⬅ Back", command=self.setup_input_screen).pack(side="right", padx=5)
        
        content_frame = ttk.Frame(self.main_container)
        content_frame.pack(fill='both', expand=True)
        ResultsTableScreen(content_frame, self.output_df)

    def export_results(self):
        if self.output_df is None: return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.output_df.to_csv(file_path, index=False)
            messagebox.showinfo("Success", f"Results exported to {file_path}")

    def show_squad_visualizer(self, tactic):
        vis_win = tk.Toplevel(self.root)
        SquadVisualizer(vis_win, self.output_df, tactic)


class TacticalBoardEditor:
    """Interactive FM24-style tactical board editor."""
    
    def __init__(self, window, weights, default_tactic):
        self.window = window
        self.weights = weights
        self.confirmed_tactic = None
        self.window.title("Tactical Board Editor")
        self.window.geometry("1100x900")
        
        # Fixed position for each grid cell (row, col) -> position_str
        self.grid_positions = self.create_grid_positions()
        
        # Current formation configuration: (row, col) -> role
        self.formation = {}
        
        # Initialize from default tactic
        self.init_from_tactic(default_tactic)
        
        # Draw UI
        self.build_ui()
    
    def create_grid_positions(self):
        """Create fixed position mapping for each grid cell."""
        grid_pos = {}
        
        # Row 0: Strikers (ST)
        grid_pos[(0, 0)] = "-"
        grid_pos[(0, 1)] = "ST, CL"
        grid_pos[(0, 2)] = "ST, C"
        grid_pos[(0, 3)] = "ST, CR"
        grid_pos[(0, 4)] = "-"
        
        # Row 1: Attacking Midfielders (AM)
        grid_pos[(1, 0)] = "AM, L"
        grid_pos[(1, 1)] = "AM, CL"
        grid_pos[(1, 2)] = "AM, C"
        grid_pos[(1, 3)] = "AM, CR"
        grid_pos[(1, 4)] = "AM, R"
        
        # Row 2: Midfielders (M)
        grid_pos[(2, 0)] = "M, L"
        grid_pos[(2, 1)] = "M, CL"
        grid_pos[(2, 2)] = "M, C"
        grid_pos[(2, 3)] = "M, CR"
        grid_pos[(2, 4)] = "M, R"
        
        # Row 3: Defensive Midfielders (DM) & Wing-Backs (WB)
        grid_pos[(3, 0)] = "WB, L"
        grid_pos[(3, 1)] = "DM, CL"
        grid_pos[(3, 2)] = "DM, C"
        grid_pos[(3, 3)] = "DM, CR"
        grid_pos[(3, 4)] = "WB, R"
        
        # Row 4: Defenders (D)
        grid_pos[(4, 0)] = "D, L"
        grid_pos[(4, 1)] = "D, CL"
        grid_pos[(4, 2)] = "D, C"
        grid_pos[(4, 3)] = "D, CR"
        grid_pos[(4, 4)] = "D, R"
        
        # Row 5: Goalkeeper (GK)
        grid_pos[(5, 0)] = "-"
        grid_pos[(5, 1)] = "-"
        grid_pos[(5, 2)] = "GK"
        grid_pos[(5, 3)] = "-"
        grid_pos[(5, 4)] = "-"
        
        return grid_pos
    
    def init_from_tactic(self, tactic):
        """Initialize formation using exact matches for the UI board."""
        for pos_str, role in tactic:
            # 1. Clean up the input (handle list or string)
            if isinstance(pos_str, (list, str)):
                full_pos = pos_str if isinstance(pos_str, str) else ", ".join(pos_str)
                #is_central_neutral = full_pos.startswith("DM") or full_pos.startswith("GK")
                #match_found = False

                # 2. Find the EXACT grid cell for this specific position string
                # This prevents "ST, C" from being snapped into the "ST, CL" slot
                for (row, col), grid_pos in self.grid_positions.items():
                    if (row, col) in self.formation:
                        continue
                    
                    #if grid_pos == full_pos or (is_central_neutral and grid_pos.startswith(full_pos.split(',')[0])):
                    if grid_pos == full_pos:
                        self.formation[(row, col)] = role
                        break
                    
    def build_ui(self):
        """Build the tactical editor interface."""
        # Header
        header = tk.Label(self.window, text="Tactical Board Editor - Click positions to select role (dropdown)", 
                         font=("Arial", 11, "bold"))
        header.pack(pady=10)
        
        # Canvas frame
        canvas_frame = ttk.Frame(self.window)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(canvas_frame, bg="#2d5016", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.on_canvas_rightclick)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        self.canvas_width = 800
        self.canvas_height = 700
        self.draw_board()
        
        # Button frame
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Load Default", command=self.load_default).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="✓ Confirm", command=self.confirm_tactic).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="✕ Cancel", command=self.window.destroy).pack(side="right", padx=5)
    
    def on_canvas_resize(self, event):
        """Handle canvas resize."""
        self.canvas_width = event.width
        self.canvas_height = event.height
        self.redraw()
    
    def on_canvas_click(self, event):
        """Handle canvas click to select role for position."""
        row, col = self.get_grid_cell(event.x, event.y)
        if row is None:
            return
        
        # Get the fixed position for this cell
        position = self.grid_positions.get((row, col))
        if not position:
            return
        
        self.show_role_selector(row, col, position)
    
    def on_canvas_rightclick(self, event):
        """Handle right-click to remove position."""
        row, col = self.get_grid_cell(event.x, event.y)
        if row is None or (row, col) not in self.formation:
            return
        
        del self.formation[(row, col)]
        self.redraw()
    
    def get_grid_cell(self, x, y):
        """Get grid cell (row, col) from canvas coordinates."""
        padding = int(0.05 * self.canvas_width)
        pitch_w = self.canvas_width - 2 * padding
        pitch_h = self.canvas_height - 2 * padding
        
        if x < padding or x > padding + pitch_w or y < padding or y > padding + pitch_h:
            return None, None
        
        cell_w = pitch_w / 5
        cell_h = pitch_h / 6
        
        col = int((x - padding) / cell_w)
        row = int((y - padding) / cell_h)
        
        return row, col
    
    def show_role_selector(self, row, col, position):
        """Show a dropdown dialog to select role for this position."""
        parts = [p.strip() for p in position.split(',')]
        area = parts[0]
        
        # FIX: Neutralize DM and GK positions for role lookup
        if area in ["DM", "GK"]:
            lookup_position = area
        elif len(parts) > 1:
            side_first = parts[1][0].upper()
            lookup_position = f"{area}, {side_first}"
        else:
            lookup_position = position
        
        # Get compatible roles for this position
        compatible_roles = []

        for role, positions in self.role_position_map.items():
            for pos_list in positions:
                if ", ".join(pos_list) == lookup_position:
                    compatible_roles.append(role)
                    break
        
        # ... (rest of the method remains the same)
        
        if not compatible_roles:
            messagebox.showwarning("No Roles", f"No compatible roles found for {lookup_position}")
            return
        
        current_role = self.formation.get((row, col), '')
        
        # Create dialog
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Select Role for {position}")
        dialog.geometry("350x150")
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(dialog, text=f"Position: {position}", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Label(dialog, text="Tactical Role:").pack(pady=5)
        
        role_combo = ttk.Combobox(dialog, values=compatible_roles, width=30, state="readonly")
        role_combo.set(current_role if current_role in compatible_roles else compatible_roles[0])
        role_combo.pack(pady=5)
        
        def save():
            role = role_combo.get()
            if role:
                self.formation[(row, col)] = role
                self.redraw()
                dialog.destroy()
        
        ttk.Button(dialog, text="✓ Save", command=save).pack(pady=10)
    
    def clear_all(self):
        """Clear all positions."""
        self.formation.clear()
        self.redraw()
    
    def load_default(self):
        """Load default tactic."""
        self.formation.clear()
        self.init_from_tactic([
            ("GK", "Sweeper Keeper (At)"),
            ("D, R", "Complete Wing-Back (Su)"),
            ("D, CR", "Central Defender (De)"),
            ("D, CL", "Central Defender (De)"),
            ("D, L", "Complete Wing-Back (At)"),
            ("DM, C", "Ball Winning Midfielder DM (De)"), 
            ("M, CR", "Advanced Playmaker CM (At)"), 
            ("M, CL", "Mezzala (Su)"),
            ("AM, R", "Winger (At)"),
            ("AM, L", "Inside Forward (Su)"),            
            ("ST, C", "Advanced Forward (At)")
        ])
        self.redraw()
    
    def confirm_tactic(self):
        """Confirm and save the tactic."""
        if not self.formation:
            messagebox.showwarning("Empty Tactic", "Please add at least one position to the formation.")
            return
        
        # Convert formation dict to list of (pos, role) tuples, sorted by row then col
        sorted_items = sorted(self.formation.items())
        
        # Normalize positions: convert to first letter of side only (L, C, R, CL, CR -> C only)
        normalized_tactic = []
        for (r, c), role in sorted_items:
            pos = self.grid_positions.get((r, c))
            parts = [p.strip() for p in pos.split(',')]
            area = parts[0]

            # Normalize position with DM and GK side removal
            if area in ["DM", "GK"]:
                normalized_pos = area
            elif len(parts) > 1:
                side_letter = parts[1][0].upper()
                normalized_pos = f"{area}, {side_letter}"
            else:
                normalized_pos = pos

            normalized_tactic.append((normalized_pos, role))
        
        self.confirmed_tactic = normalized_tactic
        
        if DEBUG:
            print(f"[DEBUG 10] Confirmed tactic: {self.confirmed_tactic}")
        
        self.window.destroy()
    
    def redraw(self):
        """Redraw the board."""
        self.canvas.delete("all")
        self.draw_board()
    
    def draw_board(self):
        """Draw the tactical pitch with grid."""
        padding = int(min(self.canvas_width,self.canvas_height) * 0.05)
        pitch_w = self.canvas_width - 2 * padding
        pitch_h = self.canvas_height - 2 * padding

        if pitch_w <= 0 or pitch_h <= 0:
            return
        
        # Draw pitch
        self.canvas.create_rectangle(padding, padding, padding + pitch_w, padding + pitch_h,
                                    outline="white", fill="#2d5016", width=2)
        
        # Center line
        self.canvas.create_line(padding + pitch_w // 2, padding, padding + pitch_w // 2,
                               padding + pitch_h, fill="white", width=1)
        
        cell_w = pitch_w / 5
        cell_h = pitch_h / 6
        circle_radius = min(cell_w, cell_h) * 0.35
        base_font_size = max(6, int(circle_radius * 0.4))
        
        # Draw grid and positions
        for row in range(6):
            for col in range(5):
                cx = padding + col * cell_w + cell_w / 2
                cy = padding + row * cell_h + cell_h / 2
                
                # Draw grid cell border
                x1, y1 = padding + col * cell_w, padding + row * cell_h
                x2, y2 = x1 + cell_w, y1 + cell_h
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="#555555", width=1)
                
                # Get fixed position for this cell
                position = self.grid_positions.get((row, col), '-')
                if position == '-': continue
                
                # Draw position if configured with role
                if (row, col) in self.formation:
                    role = self.formation[(row, col)]
                    
                    # Draw circle
                    self.canvas.create_oval(cx - circle_radius, cy - circle_radius,
                                           cx + circle_radius, cy + circle_radius,
                                           fill="#1565c0", outline="yellow", width=2)
                    
                    # Position abbreviation: simple first-letter format
                    parts = position.split(',')
                    area = parts[0].strip() # "DM", "AM", "ST", "GK"

                    if len(parts) > 1:
                        side = parts[1].strip()[0]
                        pos_text = f"{area}{side}"
                    else:
                        pos_text = area

                    #pos_text = parts[0].strip()[0] + (parts[1].strip()[0].upper() if len(parts) > 1 else "GK")  # e.g., "DC", "DL", "GK"
                    self.canvas.create_text(cx, cy - circle_radius * 0.4, text=pos_text,
                                           fill="white", font=("Arial", 8, "bold"))
                    
                    # Role abbreviation
                    role_text = role.split('(')[0].strip()[:8]
                    self.canvas.create_text(cx, cy + circle_radius * 0.4, text=role_text,
                                           fill="gold", font=("Arial", int(base_font_size*0.8), "italic"))
                else:
                    # Empty cell - show position hint
                    parts = position.split(',')
                    pos_hint = parts[0] + parts[1]
                    
                    self.canvas.create_oval(cx - circle_radius * 0.5, cy - circle_radius * 0.5,
                                           cx + circle_radius * 0.5, cy + circle_radius * 0.5,
                                           outline="#666666", width=1, dash=(2, 2))
                    
                    self.canvas.create_text(cx, cy, text=pos_hint,
                                           fill="#888888", font=("Arial", int(base_font_size *0.7)))


class ResultsTableScreen:
    def __init__(self, parent, df):
        self.parent = parent
        self.df = df.copy()
        self.filtered_df = self.df.copy()
        # Ensure these keys match the columns in output_df
        self.column_names = [
            "UID", "Name", "Squad", "Decision", 
            "Assigned Role", "Current Quality", "Potential Estimate", "Transfer Value"
        ]
        self.col_widths = {
            "UID": 60, "Name": 150, "Squad": 100, "Decision": 140, 
            "Assigned Role": 160, "Current Quality": 100, "Potential Estimate": 100, "Transfer Value": 100
        }
        self.build_filter_and_tree()

    def build_filter_and_tree(self):
        """Create filter row and treeview with proper synchronized scrolling."""
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill="both", expand=True)
        
        # Filter row using ttk.Frame with proper column widths
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill="x", padx=0, pady=0, side="top")

        filter_frame.config(height=40)
        filter_frame.pack_propagate(False)
        
        self.filter_widgets = {}
        self.filter_entries = {}
        for i, col in enumerate(self.column_names):
            width = self.col_widths.get(col, 100)
            filt_box = ttk.Frame(filter_frame, width=width)
            filt_box.pack(side="left", fill="both", padx=1)
            filt_box.pack_propagate(False)
            
            label = tk.Label(filt_box, text=f"🔍 {col}", font=("Arial", 8, "bold"), bg="#e0e0e0", fg="navy", height=1)
            label.pack(fill="x")
            
            entry = ttk.Entry(filt_box, width=int(width/8))
            entry.pack(fill="both", expand=True, padx=2, pady=2)
            entry.bind("<KeyRelease>", lambda e, c=col: self.apply_filters())
            
            self.filter_widgets[col] = filt_box
            self.filter_entries[col] = entry        

        # Treeview with scrollbars
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True, padx=0, pady=5)
        
        self.tree = ttk.Treeview(tree_frame, columns=self.column_names, show='headings', height=25)
        
        for col in self.column_names:
            width = self.col_widths.get(col, 100)
            self.tree.column(col, width=width, anchor="w")
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        self.populate_table()

    def populate_table(self):
        # if DEBUG: print(f"[DEBUG]\nFiltered_df:\n{self.filtered_df}")
        """Populate Treeview with data."""
        treeview_data = pd.DataFrame()
        # if DEBUG: print(f"[DEBUG] filtered_df columns:\n{self.filtered_df.columns}")
        # filtered_df is OK
        for idx, row in self.filtered_df.iterrows():
            values = []
            for col in self.column_names:
                val = row.get(col, "")
                # if DEBUG: print(f"[DEBUG] val:\n{val}\n")
                if isinstance(val, float):
                    val = f"{val:.2f}"
                values.append(str(val))
            values_df = pd.DataFrame(values)
            values_df = values_df.T
            treeview_data = pd.concat([treeview_data, values_df])
            #print(values_df)
            self.tree.insert("", "end", values=values)

    def sort_by_column(self, col):
        """Sort table by column."""
        self.filtered_df = self.filtered_df.sort_values(by=col, ascending=True)
        self.tree.delete(*self.tree.get_children())
        self.populate_table()

    def apply_filters(self):
        """Apply all active filters to the dataframe."""
        self.filtered_df = self.df.copy()
        
        for col, entry in self.filter_entries.items():
            search_term = entry.get().lower()
            if search_term:
                self.filtered_df = self.filtered_df[self.filtered_df[col].astype(str).str.lower().str.contains(search_term, na=False)]
        
        self.tree.delete(*self.tree.get_children())
        self.populate_table()


class SquadVisualizer:
    """Enhanced tactical pitch with rectangular player cards and role display."""
    
    def __init__(self, window, df, tactic):
        self.window = window
        self.df = df
        self.tactic = tactic
        self.window.title("Tactical Board - Squad Visualizer")
        self.window.geometry("1000x1100")
        
        self.squad_options = ["Senior Team", "B Team", "U23 Team", "U19 Team"]
        self.squad_var = tk.StringVar(value="Senior Team")
        
        header_frame = ttk.Frame(window)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(header_frame, text="Squad Selection:", font=("Arial", 11, "bold")).pack(side="left", padx=5)
        ttk.OptionMenu(header_frame, self.squad_var, self.squad_options[0], *self.squad_options, command=self.redraw_board).pack(side="left", padx=5)
        
        canvas_frame = ttk.Frame(self.window)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(canvas_frame, bg="#2d5016", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas_width = 850
        self.canvas_height = 950
        self.squad_var.trace_add("write", lambda *args: self.redraw_board())

    def on_canvas_resize(self, event):
        self.canvas_width = event.width
        self.canvas_height = event.height
        self.redraw_board()

    def redraw_board(self, *args):
        self.canvas.delete("all")
        self.draw_board()

    def truncate_name(self, name, max_len=14):
        if not isinstance(name, str) or len(name) <= max_len: return name
        parts = name.split()
        if len(parts) > 1: return f"{parts[0][0]}. {' '.join(parts[1:])}"[:max_len]
        return name[:max_len]

    def draw_board(self):
        w, h = self.canvas_width, self.canvas_height
        padding = int(min(w, h) * 0.05)
        pitch_w = w - 2 * padding
        pitch_h = h - 2 * padding
        if pitch_w <= 0 or pitch_h <= 0: return

        row_mapping = {'ST': 0, 'AM': 1, 'M': 2, 'DM': 3, 'WB': 3, 'D': 4, 'GK': 5}

        # 1. Background Pitch
        self.canvas.create_rectangle(padding, padding, padding + pitch_w, padding + pitch_h, outline="white", fill="#2d5016", width=2)
        self.canvas.create_line(padding + pitch_w // 2, padding, padding + pitch_w // 2, padding + pitch_h, fill="white", width=1)

        # Filter by selected squad (Senior, B, etc.)
        squad_df = self.df[self.df['Squad'] == self.squad_var.get()]
        players_by_row = {i: [] for i in range(6)}
        used_uids = set() # Track to prevent duplicates in identical roles (e.g. 2 CBs)

        for pos_def, role in self.tactic:
            # Normalize area and side for row placement
            if isinstance(pos_def, list):
                area = pos_def[0].strip()
                side = pos_def[1].strip() if len(pos_def) > 1 else "C"
            else:
                parts = pos_def.split(',')
                area = parts[0].strip()
                side = parts[1].strip() if len(parts) > 1 else "C"
            
            row_idx = row_mapping.get(area, 4)

            # FIND STARTER (#1): Match by Role and Decision, excluding already used UIDs
            p1_match = squad_df[
                (squad_df['Assigned Role'] == role) & 
                (squad_df['Decision'].str.contains("#1")) &
                (~squad_df.index.isin(used_uids))
            ].sort_values('Current Quality', ascending=False)

            p1 = p1_match.iloc[0] if not p1_match.empty else None
            # if DEBUG: print(f"[DEBUG] p1:\n{p1}")
            if p1 is not None: used_uids.add(p1.name)

            # FIND SUB (#2): Match by Role and Decision, excluding already used UIDs
            p2_match = squad_df[
                (squad_df['Assigned Role'] == role) & 
                (squad_df['Decision'].str.contains("#2")) &
                (~squad_df.index.isin(used_uids))
            ].sort_values('Current Quality', ascending=False)

            p2 = p2_match.iloc[0] if not p2_match.empty else None
            if p2 is not None: used_uids.add(p2.name)

            players_by_row[row_idx].append({
                'name': self.truncate_name(p1['Name']) if p1 is not None else "Empty",
                'sub': self.truncate_name(p2['Name']) if p2 is not None else None,
                'potential': round(p1['Potential Estimate']) if p1 is not None else 0,
                'side': side,
                'role': role.split('(')[0].strip(),
                'uid': p1.name if p1 is not None else None
            })
            
        # 3. Draw Player Cards
        cell_h = pitch_h / 6
        card_w = pitch_w * 0.16
        card_h = cell_h * 0.7
        
        for r_idx, players in players_by_row.items():
            if not players: continue
            
            # Sort L -> R
            side_order = {'L': 0, 'CL': 1, 'C': 2, 'CR': 3, 'R': 4}
            players.sort(key=lambda x: side_order.get(x['side'], 2))
            
            num_p = len(players)
            cy = padding + r_idx * cell_h + (cell_h / 2)
            
            for i, p in enumerate(players):
                # Calculate CX
                cx = padding + (pitch_w * (i + 1) / (num_p + 1))
                if p['side'] == 'L' and num_p > 1: cx = padding + (pitch_w * 0.12)
                if p['side'] == 'R' and num_p > 1: cx = padding + (pitch_w * 0.88)

                # Card Rectangle
                color = "#1565c0" if p['name'] != "Empty" else "#424242"
                self.canvas.create_rectangle(cx - card_w/2, cy - card_h/2, cx + card_w/2, cy + card_h/2, 
                                            fill=color, outline="white", width=1)
                
                # Header: Role
                self.canvas.create_text(cx, cy - card_h*0.3, text=p['role'], fill="#bbdefb", 
                                       font=("Arial", max(6, int(card_h*0.18)), "italic"))
                
                # Center: Name
                self.canvas.create_text(cx, cy - card_h*0.05, text=p['name'], fill="white", 
                                       font=("Arial", max(8, int(card_h*0.22)), "bold"))
                
                # Footer: Potential
                if p['potential'] > 0:
                    self.canvas.create_text(cx, cy + card_h*0.3, text=f"★ {p['potential']}", fill="gold", 
                                           font=("Arial", max(8, int(card_h*0.2)), "bold"))
                
                # Sub (outside/below card)
                if p['sub']:
                    self.canvas.create_text(cx, cy + card_h*0.5 + 10, text=f"Sub: {p['sub']}", fill="#b0bec5", 
                                           font=("Arial", max(6, int(card_h*0.15)), "italic"))

if __name__ == "__main__":
    root = tk.Tk()
    app = SquadSelectorApp(root)
    root.mainloop()
