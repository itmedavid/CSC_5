/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/cppFiles/main.cc to edit this template
 */

/* 
 * File:   main.cpp
 * Author: David
 *
 * Created on February 22, 2025, 12:31 PM
 */

#include <cstdlib>
#include <iostream>

using namespace std;

/*
 * 
 */
int main(int argc, char** argv) {
   
// Init variables 
    int pounds = 190; // Recording base weight 
    
    
// Calculations
    float stones = pounds / 150;  // Calculating stone weight  
    float kilgrms = stones * 6.35; // Calculating kilogram weight 

    
// Display output 
    cout << "Weight in stones: " << stones << endl; // Displaying weight in stones 
    cout << "Weight in kilograms: " << kilgrms << endl; // Displaying weight in kilograms

    return 0;
}

