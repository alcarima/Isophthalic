import tkinter as tk
from tkinter import messagebox

def update_color():
    try:
        r = int(entry_r.get())
        g = int(entry_g.get())
        b = int(entry_b.get())

        if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
            messagebox.showerror("Error", "RGB values must be between 0 and 255")
            return

        color = f"#{r:02x}{g:02x}{b:02x}"
        canvas.itemconfig(circle, fill=color)
        label_result.config(text=f"RGB = ({r}, {g}, {b})    HEX = {color.upper()}")

    except Exception as e:
        messagebox.showerror("Error", f"Invalid input: {e}")

root = tk.Tk()
root.title("RGB Circle")
root.geometry("500x500")

canvas = tk.Canvas(root, width=300, height=250, bg="white")
canvas.pack(pady=20)

circle = canvas.create_oval(75, 25, 225, 175, fill="#000000", outline="black", width=2)

frame = tk.Frame(root)
frame.pack(pady=10)

tk.Label(frame, text="R").grid(row=0, column=0, padx=5, pady=5)
entry_r = tk.Entry(frame, width=8)
entry_r.grid(row=0, column=1, padx=5)
entry_r.insert(0, "255")

tk.Label(frame, text="G").grid(row=1, column=0, padx=5, pady=5)
entry_g = tk.Entry(frame, width=8)
entry_g.grid(row=1, column=1, padx=5)
entry_g.insert(0, "0")

tk.Label(frame, text="B").grid(row=2, column=0, padx=5, pady=5)
entry_b = tk.Entry(frame, width=8)
entry_b.grid(row=2, column=1, padx=5)
entry_b.insert(0, "0")

btn = tk.Button(root, text="Update Color", command=update_color)
btn.pack(pady=10)

label_result = tk.Label(root, text="RGB = (255, 0, 0)    HEX = #FF0000")
label_result.pack(pady=10)

update_color()

root.mainloop()