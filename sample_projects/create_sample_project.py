
from pathlib import Path

project_root = Path(__file__).parent / "EmployeeManagementSystem"

files = {
    "include/Employee.h": """
#ifndef EMPLOYEE_H
#define EMPLOYEE_H

#include <string>

class Employee {
public:
    Employee(int id, std::string name, double basicSalary);

    int getId() const;
    std::string getName() const;
    double getBasicSalary() const;

private:
    int id;
    std::string name;
    double basicSalary;
};

#endif
""",

    "include/Salary.h": """
#ifndef SALARY_H
#define SALARY_H

class Salary {
public:
    double calculateSalary(double basicSalary, double bonus);
};

#endif
""",

    "include/Department.h": """
#ifndef DEPARTMENT_H
#define DEPARTMENT_H

#include <string>

class Department {
public:
    Department(int id, std::string name);
    std::string getDepartmentName() const;

private:
    int id;
    std::string name;
};

#endif
""",

    "include/EmployeeService.h": """
#ifndef EMPLOYEE_SERVICE_H
#define EMPLOYEE_SERVICE_H

#include "Employee.h"
#include "Salary.h"

class EmployeeService {
public:
    double getEmployeeSalary(const Employee& employee, double bonus);

private:
    Salary salaryCalculator;
};

#endif
""",

    "src/Employee.cpp": """
#include "Employee.h"

Employee::Employee(int id, std::string name, double basicSalary)
    : id(id), name(name), basicSalary(basicSalary) {}

int Employee::getId() const { return id; }

std::string Employee::getName() const { return name; }

double Employee::getBasicSalary() const { return basicSalary; }
""",

    "src/Salary.cpp": """
#include "Salary.h"

double Salary::calculateSalary(double basicSalary, double bonus) {
    return basicSalary + bonus;
}
""",

    "src/Department.cpp": """
#include "Department.h"

Department::Department(int id, std::string name)
    : id(id), name(name) {}

std::string Department::getDepartmentName() const {
    return name;
}
""",

    "src/EmployeeService.cpp": """
#include "EmployeeService.h"

double EmployeeService::getEmployeeSalary(
    const Employee& employee, double bonus) {

    return salaryCalculator.calculateSalary(
        employee.getBasicSalary(), bonus
    );
}
""",

    "src/main.cpp": """
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
""",

    "tests/SalaryTest.cpp": """
#include "Salary.h"
#include <cassert>

int main() {
    Salary salary;
    assert(salary.calculateSalary(30000, 5000) == 35000);
    return 0;
}
""",

    "docs/architecture.md": """
# Employee Management System

## Modules
- Employee: Stores employee details.
- Salary: Calculates employee salary.
- Department: Stores department information.
- EmployeeService: Uses Employee and Salary to calculate employee salary.

## Testing
- SalaryTest validates salary calculation.
"""
}

for relative_path, content in files.items():
    file_path = project_root / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content.strip() + "\n", encoding="utf-8")

print("Sample C++ project created successfully!")
print("Project location:", project_root)
