#include "Salary.h"

double Salary::calculateSalary(double basicSalary, double bonus) {
    double hra = basicSalary * 0.20;
    double da = basicSalary * 0.10;

    return basicSalary + hra + da + bonus;
}