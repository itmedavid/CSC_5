/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/cppFiles/main.cc to edit this template
 */

/* 
 * File:   main.cpp
 * Author: David
 *
 * Created on February 24, 2025, 7:53 PM
 */

#include <cstdlib>
#include <iostream>

using namespace std;

/*
 * 
 */
int main(int argc, char** argv) 
{

    // Init variables 
    float milBdgt,fedBdgt,mlPrcnt;
    
    // Defining variables 
    milBdgt = 8.42e11f;    // Military Budget = 842 Billion   
    fedBdgt = 6.5e12f;    // Federal Budget  = 6.5 Trillion
    
    // Calculations 
    mlPrcnt = (milBdgt / fedBdgt) * 100; // Finding the percentage 
    
    // Display info
    cout << "The military budget as a percentage of the federal budget is: " << mlPrcnt << "%" << endl; 
    return 0;
}

