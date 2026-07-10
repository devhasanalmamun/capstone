import pandas as pd
import numpy as np
import random
import string

def main():
    print("Loading data.csv...")
    df = pd.read_csv('data.csv', encoding='ISO-8859-1')
    print(f"Loaded {len(df)} rows.")

    # Find unique non-null CustomerID values
    unique_customers = df['CustomerID'].dropna().unique()
    unique_customers = sorted(unique_customers)
    print(f"Found {len(unique_customers)} unique customers.")

    if len(unique_customers) < 2:
        print("Error: Less than 2 unique customers found.")
        return

    # Set random seed for reproducible passwords
    random.seed(42)

    # Generate mapping of CustomerID to Email and Password
    email_map = {}
    password_map = {}

    # Set the first two customers to user's desired credentials
    email_map[unique_customers[0]] = "tahmidulislamfahim@gmail.com"
    password_map[unique_customers[0]] = "12345678"

    email_map[unique_customers[1]] = "dev.hasan@gmail.com"
    password_map[unique_customers[1]] = "12345678"

    def gen_random_password():
        return "".join(random.choices(string.ascii_letters + string.digits, k=8))

    for cid in unique_customers[2:]:
        email_map[cid] = f"customer_{int(cid)}@example.com"
        password_map[cid] = gen_random_password()

    # Map values to the dataframe
    print("Mapping Email and Password columns...")
    df['Email'] = df['CustomerID'].map(email_map)
    df['Password'] = df['CustomerID'].map(password_map)

    # Save to data.csv
    print("Writing modified CSV back to data.csv...")
    df.to_csv('data.csv', index=False, encoding='ISO-8859-1')
    print("Successfully updated database columns!")

if __name__ == '__main__':
    main()
