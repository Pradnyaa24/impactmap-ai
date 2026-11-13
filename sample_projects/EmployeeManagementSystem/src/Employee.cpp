#include "Employee.h"

Employee::Employee(int id, std::string name, double basicSalary)
    : id(id), name(name), basicSalary(basicSalary) {}

int Employee::getId() const { return id; }

std::string Employee::getName() const { return name; }

double Employee::getBasicSalary() const { return basicSalary; }
