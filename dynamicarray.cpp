#include <iostream> 
#include <string>
#include <vector>
#include <algorithm>
#include <limits>

class DynamicArray 
{
  private:
      int* data;     // pointer to the array's memory
      int size;      // current number of elements in the array
      int capacity; // capacity 

  public: 

    DynamicArray(int initalCap) 
    { 
      capacity = initalCap; 
      size = 0; 
      data = new int[capacity]; 
    }

    int get(int i) 
    {
      // Implement 

    }

    void set(int i, int val) 
    {
      //imp
    }

    void push_back(int val)
    {
      //imp 
    }

    int pop_back()
    {
      // imp 
      return 0; 
    }

    int getSize() 
    {
      // imp 
      return 0; 
    }

    int getCapacity() 
    {
      // TODO: implement
      return 0; // temporary
    }
}; 


int main () 
{
  DynamicArray arr(5);
  std::cout << "Size: " << arr.getSize() << std::endl;
  std::cout << "Capacity: " << arr.getCapacity() << std::endl;
    
  return 0; 
}