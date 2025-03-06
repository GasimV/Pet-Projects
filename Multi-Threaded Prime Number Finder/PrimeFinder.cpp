#include "PrimeFinder.h"
#include <iostream>
#include <cmath>
#include <thread>
#include <algorithm>
#include <fstream>

PrimeFinder::PrimeFinder(int start, int end, int numThreads)
    : startRange(start), endRange(end), numThreads(numThreads) {}

void PrimeFinder::findPrimes() {
    std::vector<std::thread> threads;
    int chunkSize = (endRange - startRange + 1) / numThreads;

    for (int i = 0; i < numThreads; ++i) {
        int start = startRange + i * chunkSize;
        int end = (i == numThreads - 1) ? endRange : start + chunkSize - 1;

        threads.emplace_back(&PrimeFinder::worker, this, start, end);
    }

    for (auto& thread : threads) {
        thread.join();
    }
    
    // Sort primes to maintain correct order
    std::sort(primes.begin(), primes.end());
}

void PrimeFinder::worker(int start, int end) {
    std::vector<int> localPrimes;

    for (int num = start; num <= end; ++num) {
        if (isPrime(num)) {
            localPrimes.push_back(num);
        }
    }

    // Safely add found primes to the shared vector
    std::lock_guard<std::mutex> lock(primesMutex);
    primes.insert(primes.end(), localPrimes.begin(), localPrimes.end());
}

bool PrimeFinder::isPrime(int num) {
    if (num < 2) return false;
    if (num == 2 || num == 3) return true;
    if (num % 2 == 0 || num % 3 == 0) return false;

    for (int i = 5; i * i <= num; i += 6) {
        if (num % i == 0 || num % (i + 2) == 0)
            return false;
    }
    return true;
}

const std::vector<int>& PrimeFinder::getPrimes() const {
    return primes;
}

bool PrimeFinder::isPrimeInList(int number) const {
    return std::binary_search(primes.begin(), primes.end(), number);
}

void PrimeFinder::saveToFile(const std::string& filename) const {
    std::ofstream file(filename);
    if (!file) {
        std::cerr << "Error: Could not open file for writing.\n";
        return;
    }

    for (int prime : primes) {
        file << prime << "\n";
    }

    std::cout << "Prime numbers saved to " << filename << "\n";
}