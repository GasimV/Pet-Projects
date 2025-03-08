---

# **BMP Console Renderer** 🎨

This is a **C++ console application** that loads a **black-and-white BMP image**, displays it in the console using text symbols, draws a diagonal cross (**X**) on the image, and saves the modified result as a new BMP file.

## **Features**
✔ Reads **24-bit and 32-bit BMP images**  
✔ Displays the BMP image in the console using `#` for black and ` ` (space) for white  
✔ Draws a diagonal **X** on the image  
✔ Saves the modified BMP file  
✔ Uses **C++ STL and Windows API** (no third-party libraries)

---

## **How to Use**
1. **Compile the project** using a C++ compiler (MSVC, MinGW, Clang, etc.).
2. **Run the application** and follow the prompts.
3. **Provide the full file path** of the input BMP file (e.g., ">> Enter input BMP file path: C:\images\input.bmp").
4. **Provide the full file path** where the modified BMP should be saved (e.g., "Enter output BMP file path: C:\images\output.bmp").
5. **View the modified BMP file**.

---

## **BMP Format Restrictions**
- Only supports **black-and-white** images (`RGB(0,0,0)` for black and `RGB(255,255,255)` for white).
- Only supports **small-sized images** for clear console rendering.
- Requires **full file paths** for input and output.

---

## **Project Structure**
```
/BMP-Console-Renderer
│── README.md       # Documentation
│── bmp.cpp         # C++ source code
│── input.bmp       # Sample input image
│── output.bmp      # Sample output image
```

---

## **License**
This project is open-source**.

---

Enjoy coding! 🚀