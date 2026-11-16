
#include "Salary.h"
#include <cassert>
#include <iostream>

int main() {
    Salary salary;

    assert(salary.calculateSalary(30000, 5000) == 44000);
    assert(salary.calculateSalary(0, 5000) == 5000);
    assert(salary.calculateSalary(30000, 0) == 39000);
    assert(salary.calculateSalary(1000000, 100000) == 1400000);

    std::cout << "All Salary tests passed!" << std::endl;

    return 0;
}
