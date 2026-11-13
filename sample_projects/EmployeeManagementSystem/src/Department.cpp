#include "Department.h"

Department::Department(int id, std::string name)
    : id(id), name(name) {}

std::string Department::getDepartmentName() const {
    return name;
}
