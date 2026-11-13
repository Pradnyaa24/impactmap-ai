#include "EmployeeService.h"

double EmployeeService::getEmployeeSalary(
    const Employee& employee, double bonus) {

    return salaryCalculator.calculateSalary(
        employee.getBasicSalary(), bonus
    );
}
