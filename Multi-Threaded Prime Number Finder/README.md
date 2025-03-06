---

### **📌 Multi-Threaded Prime Number Finder**  

🚀 A simple yet efficient **C++ CLI application** that finds prime numbers in a given range using **multi-threading**. It distributes the workload across multiple threads, ensuring faster execution for large ranges.  

---

## **🌜 Features**  
👉 Accepts user input for the range (e.g., find primes between `1` and `1,000,000`).  
👉 Automatically detects **available CPU threads** and recommends an optimal thread count.  
👉 Uses **multiple threads (`std::thread`)** to distribute workload efficiently.  
👉 **Thread-safe prime storage** using `std::mutex`.  
👉 Measures and **displays execution time**.  
👉 Ensures the **output is sorted correctly** after multi-threaded execution.  
👉 Allows **searching for a specific number** in the prime list.  
👉 Option to **save primes to a file (`primes.txt`)** for large outputs.  

---

## **🤖 Technologies Used**  
- **C++11 (or later)**  
- **Multi-threading (`std::thread`)**  
- **Synchronization (`std::mutex`)**  
- **High-resolution timing (`std::chrono`)**  
- **Binary search (`std::binary_search`) for fast prime lookups**  
- **File handling (`std::ofstream`) for saving results**  

---

## **🚀 Usage**  

1️⃣ **Run the program**  
```sh
./MultiThreadedPrimeFinder
```

2️⃣ **Enter the number range** (start and end):  
```
Enter the range (start end): 1 1000000
```

3️⃣ **The program detects CPU threads** and recommends an optimal number of threads:  
```
System has 8 available threads.
Enter the number of threads (recommended: 8): 8
```

4️⃣ **Prime numbers are computed efficiently and displayed**  
```
Primes found: 78498
Time taken: 0.0872498 seconds
```

5️⃣ **Check if a number is prime**  
```
Do you want to check if a specific number is prime? (y/n): y
Enter number to search: 37
37 is a prime number.
```

6️⃣ **Save the primes to a file**  
```
Do you want to save the primes to a file? (y/n): y
Prime numbers saved to primes.txt
```

---

## **📊 Performance Example**
For **1 to 10,000,000** with 4 threads:
```
Primes found: 664579
Time taken: 0.715531 seconds
```

For **1 to 10,000,000** with 1 thread:
```
Primes found: 664579
Time taken: 1.66443 seconds
```
💪 **Multi-threading significantly speeds up execution!**  

---

## **🛠 Future Enhancements**
🔹 Optimize further using **Sieve of Eratosthenes**.  
🔹 Implement **GUI (Qt) visualization**.  

---

## **📚 License**  
🗄 This project is **open-source** and free to use.  

---

### **💡 Contribute & Improve**
Feel free to **fork** and improve the project! Contributions are welcome. 🚀  

---