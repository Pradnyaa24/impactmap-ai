#include <iostream>
#include "Employee.h"
#include "EmployeeService.h"

int main() {
    Employee employee(1, "Rahul", 30000);
    EmployeeService service;

    double salary = service.getEmployeeSalary(employee, 5000);

    std::cout << "Employee: " << employee.getName() << std::endl;
    std::cout << "Salary: " << salary << std::endl;

    return 0;
}
