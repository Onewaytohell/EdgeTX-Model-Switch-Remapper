import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import os

SWITCHES = ["SA", "SB", "SC", "SD", "SE", "SF", "SG", "SH"]

class BatchSwitchRemapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EdgeTX Batch Switch Remapper")
        self.root.geometry("560x580")
        self.root.resizable(False, False)

        self.input_folder = None
        self.output_folder = None
        self.rows = []

        self._build_ui()

    def _build_ui(self):
        pad = dict(padx=10, pady=6)

        tk.Label(self.root, text="EdgeTX Batch Switch Remapper", font=("Segoe UI", 14, "bold")).pack(pady=(14, 2))
        tk.Label(self.root, text="Apply switch remapping to all .yml model files in a folder", font=("Segoe UI", 9), fg="gray").pack()

        # Input folder
        in_frame = tk.LabelFrame(self.root, text="Input Folder (models to convert)", font=("Segoe UI", 9), padx=8, pady=6)
        in_frame.pack(fill="x", **pad)
        self.in_label = tk.Label(in_frame, text="No folder selected", anchor="w", fg="gray", font=("Segoe UI", 9))
        self.in_label.pack(side="left", fill="x", expand=True)
        tk.Button(in_frame, text="Browse...", command=self._browse_input, width=10).pack(side="right")

        # Output folder
        out_frame = tk.LabelFrame(self.root, text="Output Folder (where to save converted files)", font=("Segoe UI", 9), padx=8, pady=6)
        out_frame.pack(fill="x", **pad)
        self.out_label = tk.Label(out_frame, text="No folder selected", anchor="w", fg="gray", font=("Segoe UI", 9))
        self.out_label.pack(side="left", fill="x", expand=True)
        tk.Button(out_frame, text="Browse...", command=self._browse_output, width=10).pack(side="right")

        # Remapping rules
        rules_frame = tk.LabelFrame(self.root, text="Switch Remapping Rules", font=("Segoe UI", 9), padx=8, pady=6)
        rules_frame.pack(fill="both", expand=True, **pad)

        header = tk.Frame(rules_frame)
        header.pack(fill="x", pady=(0, 4))
        tk.Label(header, text="From Switch", font=("Segoe UI", 9, "bold"), width=16).pack(side="left")
        tk.Label(header, text="->", font=("Segoe UI", 11)).pack(side="left", padx=8)
        tk.Label(header, text="To Switch", font=("Segoe UI", 9, "bold"), width=16).pack(side="left")

        self.rows_frame = tk.Frame(rules_frame)
        self.rows_frame.pack(fill="both", expand=True)

        btn_row = tk.Frame(rules_frame)
        btn_row.pack(fill="x", pady=(6, 0))
        tk.Button(btn_row, text="+ Add Rule", command=self._add_row, width=12).pack(side="left")
        tk.Button(btn_row, text="- Remove Last", command=self._remove_row, width=12).pack(side="left", padx=6)
        tk.Button(btn_row, text="Clear All", command=self._clear_rows, width=10).pack(side="left")

        for _ in range(3):
            self._add_row()

        # Process button
        tk.Button(
            self.root, text="Remap All Files", command=self._process,
            font=("Segoe UI", 10, "bold"), bg="#0078D4", fg="white",
            activebackground="#005A9E", activeforeground="white",
            relief="flat", padx=16, pady=6
        ).pack(pady=(4, 6))

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self.root, textvariable=self.status_var, font=("Segoe UI", 9), fg="gray").pack(pady=(0, 8))

    def _add_row(self):
        row_frame = tk.Frame(self.rows_frame)
        row_frame.pack(fill="x", pady=2)
        from_var = tk.StringVar(value=SWITCHES[0])
        to_var = tk.StringVar(value=SWITCHES[1])
        ttk.Combobox(row_frame, textvariable=from_var, values=SWITCHES, width=12, state="readonly").pack(side="left")
        tk.Label(row_frame, text="->", font=("Segoe UI", 11)).pack(side="left", padx=12)
        ttk.Combobox(row_frame, textvariable=to_var, values=SWITCHES, width=12, state="readonly").pack(side="left")
        self.rows.append((from_var, to_var, row_frame))

    def _remove_row(self):
        if self.rows:
            _, _, frame = self.rows.pop()
            frame.destroy()

    def _clear_rows(self):
        for _, _, frame in self.rows:
            frame.destroy()
        self.rows.clear()

    def _browse_input(self):
        path = filedialog.askdirectory(title="Select Input Folder")
        if path:
            self.input_folder = path
            self.in_label.config(text=path, fg="black")

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.output_folder = path
            self.out_label.config(text=path, fg="black")

    def _remap_content(self, content, rules):
        placeholders = {t: f"__SWREMAP_{t}__" for _, t in rules}
        result = content

        for f, t in rules:
            result = re.sub(
                rf'\b{re.escape(f)}(?=[012]|(?![A-Z0-9]))',
                placeholders[t],
                result
            )

        for t, placeholder in placeholders.items():
            result = result.replace(placeholder, t)

        return result

    def _process(self):
        if not self.input_folder:
            messagebox.showerror("No Input Folder", "Please select an input folder.")
            return
        if not self.output_folder:
            messagebox.showerror("No Output Folder", "Please select an output folder.")
            return

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

        yml_files = [
            f for f in os.listdir(self.input_folder)
            if f.lower().endswith(('.yml', '.yaml'))
        ]

        if not yml_files:
            messagebox.showerror("No Files", "No .yml files found in the input folder.")
            return

        success = 0
        errors = 0

        for filename in yml_files:
            in_path = os.path.join(self.input_folder, filename)
            out_path = os.path.join(self.output_folder, filename)
            try:
                with open(in_path, "r", encoding="utf-8") as fh:
                    content = fh.read()
                new_content = self._remap_content(content, rules)
                with open(out_path, "w", encoding="utf-8") as fh:
                    fh.write(new_content)
                success += 1
            except Exception as e:
                errors += 1

        summary = f"Done! {success} file(s) converted."
        if errors:
            summary += f" {errors} file(s) had errors."
        self.status_var.set(summary)
        messagebox.showinfo("Complete", f"{summary}\n\nSaved to:\n{self.output_folder}")


if __name__ == "__main__":
    root = tk.Tk()
    app = BatchSwitchRemapApp(root)
    root.mainloop()
