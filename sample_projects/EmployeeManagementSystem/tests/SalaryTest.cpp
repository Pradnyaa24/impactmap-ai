#include "Salary.h"
#include <cassert>

int main() {
    Salary salary;
    assert(salary.calculateSalary(30000, 5000) == 35000);
    return 0;
}
