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
