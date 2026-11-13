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
