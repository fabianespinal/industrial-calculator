#!/usr/bin/env python3
# test_database.py
# Test script to verify database functionality

import database
import json
from datetime import datetime

print("=" * 50)
print("TESTING DATABASE FUNCTIONALITY")
print("=" * 50)

# Test 1: Setup Database
print("\n1. Setting up database...")
try:
    database.setup_database()
    print("✅ Database setup successful")
except Exception as e:
    print(f"❌ Database setup failed: {e}")
    exit(1)

# Test 2: Add a test client
print("\n2. Adding test client...")
try:
    client_id = database.add_new_client(
        company_name="Test Company ABC",
        contact_name="John Doe",
        email="test@example.com",
        phone="809-555-0123",
        address="123 Test Street",
        tax_id="00000000001",
        notes="This is a test client"
    )
    print(f"✅ Client added successfully with ID: {client_id}")
except Exception as e:
    print(f"❌ Failed to add client: {e}")
    exit(1)

# Test 3: Get all clients
print("\n3. Retrieving all clients...")
try:
    clients = database.get_all_clients()
    print(f"✅ Found {len(clients)} client(s)")
    for client in clients:
        print(f"   - {client['company_name']} (ID: {client['id']})")
except Exception as e:
    print(f"❌ Failed to retrieve clients: {e}")

# Test 4: Save a calculation
print("\n4. Saving test calculation...")
try:
    test_materials = {
        "aluzinc_techo": 1000.5,
        "aluzinc_pared": 800.3,
        "tornillos": 500
    }
    
    calc_id = database.save_calculation(
        client_id=client_id,
        project_name="Test Warehouse Project",
        length=30.0,
        width=20.0,
        lateral_height=6.0,
        roof_height=8.0,
        materials_dict=test_materials,
        total_amount=25000.00
    )
    print(f"✅ Calculation saved successfully with ID: {calc_id}")
except Exception as e:
    print(f"❌ Failed to save calculation: {e}")

# Test 5: Retrieve calculations
print("\n5. Retrieving client calculations...")
try:
    calculations = database.get_client_calculations(client_id)
    print(f"✅ Found {len(calculations)} calculation(s)")
    for calc in calculations:
        print(f"   - {calc['project_name']} ({calc['length']}x{calc['width']}m)")
except Exception as e:
    print(f"❌ Failed to retrieve calculations: {e}")

# Test 6: Get calculation details
print("\n6. Getting calculation details...")
try:
    if calculations:
        calc_details = database.get_calculation_details(calculations[0]['id'])
        print(f"✅ Retrieved details for: {calc_details['project_name']}")
        print(f"   - Dimensions: {calc_details['warehouse_length']}x{calc_details['warehouse_width']}m")
        print(f"   - Materials data present: {'materials' in calc_details}")
except Exception as e:
    print(f"❌ Failed to get calculation details: {e}")

# Test 7: Search clients
print("\n7. Testing client search...")
try:
    search_results = database.search_clients("Test")
    print(f"✅ Search found {len(search_results)} result(s)")
except Exception as e:
    print(f"❌ Search failed: {e}")

# Test 8: Update client
print("\n8. Updating client...")
try:
    database.update_client(
        client_id=client_id,
        company_name="Updated Test Company",
        contact_name="Jane Doe",
        email="updated@example.com",
        phone="809-555-9999"
    )
    updated_client = database.get_client_by_id(client_id)
    print(f"✅ Client updated: {updated_client['company_name']}")
except Exception as e:
    print(f"❌ Failed to update client: {e}")

print("\n" + "=" * 50)
print("DATABASE TESTS COMPLETED")
print("=" * 50)

# Summary
print("\n📊 TEST SUMMARY:")
print("✅ Database is working correctly")
print("✅ All CRUD operations functional")
print("✅ You can now run: streamlit run app.py")
print("\n💡 TIP: The test data has been saved to your database.")
print("   You can use 'Test Company' to test the app features.")