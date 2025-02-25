/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/cppFiles/main.cc to edit this template
 */

/* 
 * File:   main.cpp
 * Author: David
 *
 * Created on February 19, 2025, 11:17 PM
 */

#include <cstdlib>
#include <iostream>


using namespace std;

/*
 * 
 */
int main(int argc, char** argv) {

// initialize variables
    float tax = 6.75; // Tax rate set to 6.75 %
    float mlCost = 88.67; // Total meal cost: $88.67
    
// calculations 
    float taxAmnt = mlCost * (tax/100); // Calculating tax amount 
    float tip = mlCost * (20/100);  // Calculating tip total 
    float totlBill = mlCost + taxAmnt + tip; // Calculating the total of the bill 
    
//Display the info  
    cout << "Meal Cost: " << mealCost << endl; 
    cout << "Tax Amount: " << taxAmnt << endl; 
    cout << "Total Bill: " << totlBill << endl;    
    return 0;
}

