#include "PrimeFinder.h"
#include <iostream>
#include <chrono>
#include <thread>
#include <string>

int main() {
    int start, end, numThreads;

    // Get available hardware threads
    unsigned int availableThreads = std::thread::hardware_concurrency();
    if (availableThreads == 0) {
        availableThreads = 2; // Fallback in case detection fails
    }

    std::cout << "System has " << availableThreads << " available threads.\n";

    std::cout << "Enter the range (start end): ";
    std::cin >> start >> end;

    std::cout << "Enter the number of threads (recommended: " << availableThreads << "): ";
    std::cin >> numThreads;
    
    // Ensure user does not enter more threads than available
    if (numThreads > static_cast<int>(availableThreads)) {
        std::cout << "Warning: You entered more threads than available (" << availableThreads << ").\n";
        std::cout << "Setting number of threads to " << availableThreads << ".\n";
        numThreads = availableThreads;
    }

    auto startTime = std::chrono::high_resolution_clock::now();

    PrimeFinder finder(start, end, numThreads);
    finder.findPrimes();

    auto endTime = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsedTime = endTime - startTime;

    const auto& primes = finder.getPrimes();
    std::cout << "Primes found: " << primes.size() << "\n";
    // for (int prime : primes) {
    //     std::cout << prime << " ";
    // }
    std::cout << "\n";
    std::cout << "Time taken: " << elapsedTime.count() << " seconds\n";
    
    // 🔹 Ask user if they want to search for a number
    char searchOption;
    std::cout << "Do you want to check if a specific number is prime? (y/n): ";
    std::cin >> searchOption;

    if (searchOption == 'y' || searchOption == 'Y') {
        int numberToCheck;
        std::cout << "Enter number to search: ";
        std::cin >> numberToCheck;
        if (finder.isPrimeInList(numberToCheck)) {
            std::cout << numberToCheck << " is a prime number.\n";
        } else {
            std::cout << numberToCheck << " is NOT a prime number.\n";
        }
    }

    // 🔹 Ask user if they want to save to a file
    char saveOption;
    std::cout << "Do you want to save the primes to a file? (y/n): ";
    std::cin >> saveOption;

    if (saveOption == 'y' || saveOption == 'Y') {
        finder.saveToFile("primes.txt");
    }



    return 0;
}
