/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/cppFiles/main.cc to edit this template
 */

/* 
 * File:   main.cpp
 * Author: David
 *
 * Created on February 18, 2025, 6:40 PM
 */

#include <cstdlib>
#include <iostream>
#include <string>

using namespace std;

/*
 * 
 */
int main(int argc, char** argv) {

 // Initializing the cost of items in the sale 
    float item1 = 15.95; 
    float item2 = 24.95; 
    float item3 = 6.95; 
    float item4 = 12.95; 
    float item5 = 3.95; 
    float saleTax = 7;

    
 // Logic for calculation for sale
    float subTotl = item1 + item2 + item3 + item4 + item5; // Calculating subtotal of meal 
    float grandTotal = subTotl + (subTotl * saleTax / 100); // Calculating grand total of meal 

 // Displaying item information 
    cout << "Itemized List Below" << endl; 
    cout << "Item 1: " <<  "$" << item1 << endl; 
    cout << "Item 2: " <<  "$" << item2 << endl; 
    cout << "Item 3: " <<  "$" << item3 << endl; 
    cout << "Item 4: " <<  "$" << item4 << endl; 
    cout << "Item 5: " <<  "$" << item5 << endl; 
    cout << "==================" << endl; 
    cout << "Subtotal: " << subTotl << endl; 
    cout << "Tax: " << saleTax << "%" << endl; 
    cout << "Grand Total: " << grandTotal << endl; 
    return 0;
}

