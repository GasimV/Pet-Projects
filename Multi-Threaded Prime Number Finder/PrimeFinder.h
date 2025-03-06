#ifndef PRIMEFINDER_H
#define PRIMEFINDER_H

#include <vector>
#include <mutex>
#include <string>

class PrimeFinder {
public:
    PrimeFinder(int start, int end, int numThreads);
    void findPrimes(); // Starts the multi-threaded search
    const std::vector<int>& getPrimes() const;
        
    bool isPrimeInList(int number) const;
    void saveToFile(const std::string& filename) const;

private:
    int startRange, endRange, numThreads;
    std::vector<int> primes;
    std::mutex primesMutex; // Mutex for thread-safe writing

    void worker(int start, int end); // Worker function for each thread
    bool isPrime(int num);
};

#endif // PRIMEFINDER_H
