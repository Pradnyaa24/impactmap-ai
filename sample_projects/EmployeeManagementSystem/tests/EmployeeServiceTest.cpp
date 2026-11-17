
#include "EmployeeService.h"

#include <cassert>
#include <cmath>
#include <iostream>

int main() {
    EmployeeService service;

    // Test 1: Basic salary 30000 + bonus 5000
    // HRA 6000 + DA 3000 + transport allowance 2000
    Employee employee1(1, "Test Employee", 30000);

    double salary1 = service.getEmployeeSalary(employee1, 5000);

    assert(std::abs(salary1 - 46000.0) < 0.001);

    // Test 2: Zero basic salary and bonus 5000
    Employee employee2(2, "Zero Salary", 0);

    double salary2 = service.getEmployeeSalary(employee2, 5000);

    assert(std::abs(salary2 - 7000.0) < 0.001);

    // Test 3: Basic salary 30000 and zero bonus
    Employee employee3(3, "No Bonus", 30000);

    double salary3 = service.getEmployeeSalary(employee3, 0);

    assert(std::abs(salary3 - 41000.0) < 0.001);

    std::cout << "All EmployeeService tests passed!" << std::endl;

    return 0;
}
