import tkinter as tk

print("Program started")

def update_color(value=None):
    print("update_color called")
    r = red_slider.get()
    g = green_slider.get()
    b = blue_slider.get()

    color = f"#{r:02x}{g:02x}{b:02x}"
    canvas.itemconfig(circle, fill=color)

    rgb_label.config(text=f"RGB = ({r}, {g}, {b})")
    hex_label.config(text=f"HEX = {color.upper()}")

root = tk.Tk()
print("Window created")

root.title("RGB Circle with Sliders")
root.geometry("500x500")

canvas = tk.Canvas(root, width=300, height=220, bg="white")
canvas.pack(pady=20)

circle = canvas.create_oval(75, 25, 225, 175, fill="#000000", outline="black", width=2)

rgb_label = tk.Label(root, text="RGB = (0, 0, 0)", font=("Arial", 12))
rgb_label.pack()

hex_label = tk.Label(root, text="HEX = #000000", font=("Arial", 12))
hex_label.pack(pady=(0, 10))

tk.Label(root, text="Red").pack()
red_slider = tk.Scale(root, from_=0, to=255, orient="horizontal", length=300, command=update_color)
red_slider.pack()

tk.Label(root, text="Green").pack()
green_slider = tk.Scale(root, from_=0, to=255, orient="horizontal", length=300, command=update_color)
green_slider.pack()

tk.Label(root, text="Blue").pack()
blue_slider = tk.Scale(root, from_=0, to=255, orient="horizontal", length=300, command=update_color)
blue_slider.pack()

update_color()
print("Entering mainloop")

root.mainloop()


