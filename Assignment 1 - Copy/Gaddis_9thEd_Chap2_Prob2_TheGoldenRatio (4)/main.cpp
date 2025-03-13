/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/cppFiles/main.cc to edit this template
 */

/*
 * File:   main.cpp
 * Author: David
 *
 * Created on February 22, 2025, 12:46 PM
 */

#include <cstdlib>
#include <iostream>

using namespace std;

/*
 *
 */
int main(int argc, char **argv)
{

    // Init Variables - kilocalories

    int stbrykl = 35; // Strawberry kilocalories per 100g of sugar
    int sugarkl = 40; // Sugar kilocalories per 100g of sugar
    int lemonkl = 32; // Lemon kilocalories per 100g of sugar

    int strbrry = 400;  
    int sugar = strbrry; 

    // Calculations

    double lemonjc = (strbrry / 100) * 5;
    double totljam = strbrry + sugar + lemonjc;
    double strbrcl = (strbrry / 100) * stbrykl;
    double sugarcl = (sugar / 100) * sugarkl;
    double lemoncl = (lemonjc / 100) * lemonkl;

    double totalcl = strbrcl + sugarcl + lemoncl;

    // Display output
    cout << "Total Amount of Jam: " << totljam << endl;
    cout << "Total KCalories: " << totalcl << endl;

    return 0;
}
