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
