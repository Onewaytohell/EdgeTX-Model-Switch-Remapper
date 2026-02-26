import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os

# Available switches
SWITCHES = ["SA", "SB", "SC", "SD", "SE", "SF", "SG", "SH"]

class SwitchRemapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EdgeTX Switch Remapper")
        self.root.geometry("520x520")
        self.root.resizable(False, False)

        self.input_file = None
        self.rows = []  # list of (from_var, to_var)

        self._build_ui()

    def _build_ui(self):
        pad = dict(padx=10, pady=6)

        # Title
        tk.Label(self.root, text="EdgeTX Switch Remapper", font=("Segoe UI", 14, "bold")).pack(pady=(14, 2))
        tk.Label(self.root, text="Remap switches in EdgeTX/OpenTX .yml model files", font=("Segoe UI", 9), fg="gray").pack()

        # File selection
        file_frame = tk.LabelFrame(self.root, text="Model File", font=("Segoe UI", 9), padx=8, pady=6)
        file_frame.pack(fill="x", **pad)

        self.file_label = tk.Label(file_frame, text="No file selected", anchor="w", fg="gray", font=("Segoe UI", 9))
        self.file_label.pack(side="left", fill="x", expand=True)
        tk.Button(file_frame, text="Browse...", command=self._browse_file, width=10).pack(side="right")

        # Remapping rules
        rules_frame = tk.LabelFrame(self.root, text="Switch Remapping Rules", font=("Segoe UI", 9), padx=8, pady=6)
        rules_frame.pack(fill="both", expand=True, **pad)

        # Header
        header = tk.Frame(rules_frame)
        header.pack(fill="x", pady=(0, 4))
        tk.Label(header, text="From Switch", font=("Segoe UI", 9, "bold"), width=16).pack(side="left")
        tk.Label(header, text="→", font=("Segoe UI", 11)).pack(side="left", padx=8)
        tk.Label(header, text="To Switch", font=("Segoe UI", 9, "bold"), width=16).pack(side="left")

        # Scrollable rows area
        self.rows_frame = tk.Frame(rules_frame)
        self.rows_frame.pack(fill="both", expand=True)

        # Buttons row
        btn_row = tk.Frame(rules_frame)
        btn_row.pack(fill="x", pady=(6, 0))
        tk.Button(btn_row, text="+ Add Rule", command=self._add_row, width=12).pack(side="left")
        tk.Button(btn_row, text="− Remove Last", command=self._remove_row, width=12).pack(side="left", padx=6)
        tk.Button(btn_row, text="Clear All", command=self._clear_rows, width=10).pack(side="left")

        # Add 3 default rows
        for _ in range(3):
            self._add_row()

        # Process button
        tk.Button(
            self.root, text="Remap & Save File", command=self._process,
            font=("Segoe UI", 10, "bold"), bg="#0078D4", fg="white",
            activebackground="#005A9E", activeforeground="white",
            relief="flat", padx=16, pady=6
        ).pack(pady=(4, 10))

        # Status
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self.root, textvariable=self.status_var, font=("Segoe UI", 9), fg="gray").pack(pady=(0, 8))

    def _add_row(self):
        row_frame = tk.Frame(self.rows_frame)
        row_frame.pack(fill="x", pady=2)

        from_var = tk.StringVar(value=SWITCHES[0])
        to_var = tk.StringVar(value=SWITCHES[1])

        from_cb = ttk.Combobox(row_frame, textvariable=from_var, values=SWITCHES, width=12, state="readonly")
        from_cb.pack(side="left")
        tk.Label(row_frame, text="→", font=("Segoe UI", 11)).pack(side="left", padx=12)
        to_cb = ttk.Combobox(row_frame, textvariable=to_var, values=SWITCHES, width=12, state="readonly")
        to_cb.pack(side="left")

        self.rows.append((from_var, to_var, row_frame))

    def _remove_row(self):
        if self.rows:
            _, _, frame = self.rows.pop()
            frame.destroy()

    def _clear_rows(self):
        for _, _, frame in self.rows:
            frame.destroy()
        self.rows.clear()

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select EdgeTX Model File",
            filetypes=[("YAML files", "*.yml *.yaml"), ("All files", "*.*")]
        )
        if path:
            self.input_file = path
            self.file_label.config(text=os.path.basename(path), fg="black")
            self.status_var.set(f"Loaded: {os.path.basename(path)}")

    def _process(self):
        if not self.input_file:
            messagebox.showerror("No File", "Please select a model file first.")
            return

        # Build remap list, check for duplicates/self-maps
        rules = []
        seen_from = set()
        for from_var, to_var, _ in self.rows:
            f = from_var.get()
            t = to_var.get()
            if f == t:
                messagebox.showerror("Invalid Rule", f"Cannot remap {f} to itself.")
                return
            if f in seen_from:
                messagebox.showerror("Duplicate Rule", f"Switch {f} appears more than once as a source.")
                return
            seen_from.add(f)
            rules.append((f, t))

        if not rules:
            messagebox.showerror("No Rules", "Please add at least one remapping rule.")
            return

        try:
            with open(self.input_file, "r", encoding="utf-8") as fh:
                content = fh.read()
        except Exception as e:
            messagebox.showerror("Read Error", str(e))
            return

        # We need to remap without collisions.
        # Strategy: replace in two passes using a placeholder for targets
        # that are also sources (to avoid double-remapping).
        # E.g. SA->SE, SE->SF: first replace SA->__SE__, SE->__SF__, then __SE__->SE, __SF__->SF

        # Build a safe temporary token for each target
        placeholders = {}
        for f, t in rules:
            placeholders[t] = f"__SWREMAP_{t}__"

        result = content

        # Pass 1: replace all FROM switches with placeholders of their TO value
        for f, t in rules:
            placeholder = placeholders[t]
            # Match switch references: S[A-H] followed by 0,1,2 or end of switch name
            # Covers: SA0, SA1, SA2, SA (bare), !SA0 etc.
            result = re.sub(
                rf'\b{re.escape(f)}(?=[012\b]|(?![A-Z0-9]))',
                placeholder,
                result
            )

        # Pass 2: replace placeholders with final target switch names
        for t, placeholder in placeholders.items():
            result = result.replace(placeholder, t)

        # Save output
        base, ext = os.path.splitext(self.input_file)
        out_path = base + "_remapped" + ext

        save_path = filedialog.asksaveasfilename(
            title="Save Remapped File",
            initialfile=os.path.basename(out_path),
            defaultextension=ext,
            filetypes=[("YAML files", "*.yml *.yaml"), ("All files", "*.*")]
        )
        if not save_path:
            return

        try:
            with open(save_path, "w", encoding="utf-8") as fh:
                fh.write(result)
        except Exception as e:
            messagebox.showerror("Write Error", str(e))
            return

        self.status_var.set(f"✓ Saved: {os.path.basename(save_path)}")
        messagebox.showinfo("Done", f"Remapped file saved to:\n{save_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = SwitchRemapApp(root)
    root.mainloop()
