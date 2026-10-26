import os
import csv
import json
from io import StringIO
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, Response
)
from database import (
    init_db, get_session, User, Tariff, Appliance, BillRecord, SavingScenario
)
from calculator import (
    calculate_appliance_energy, calculate_bill, analyze_appliances, CO2_PER_KWH, TREE_CO2_PER_YEAR
)
from pdf_generator import generate_pdf_report

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'smart-energy-analyzer-secure-key-2026')

# Initialize DB (creates PostgreSQL tables on Render or SQLite tables locally)
init_db()

# Appliance presets library for quick selection
APPLIANCE_PRESETS = [
    {"name": "Inverter AC 1.5 Ton (5-Star)", "category": "Cooling", "watts": 1100, "hours": 6, "standby_watts": 2, "standby_hours": 18},
    {"name": "Non-Inverter AC 1.5 Ton (Old/3-Star)", "category": "Cooling", "watts": 1750, "hours": 6, "standby_watts": 4, "standby_hours": 18},
    {"name": "Standard Ceiling Fan", "category": "Cooling", "watts": 75, "hours": 12, "standby_watts": 0, "standby_hours": 0},
    {"name": "BLDC Energy-Saver Fan", "category": "Cooling", "watts": 28, "hours": 12, "standby_watts": 0, "standby_hours": 0},
    {"name": "Double-Door Refrigerator (260L)", "category": "Kitchen", "watts": 180, "hours": 24, "standby_watts": 0, "standby_hours": 0},
    {"name": "Single-Door Refrigerator (190L)", "category": "Kitchen", "watts": 120, "hours": 24, "standby_watts": 0, "standby_hours": 0},
    {"name": "LED Room Bulb (9W)", "category": "Lighting", "watts": 9, "hours": 6, "standby_watts": 0, "standby_hours": 0},
    {"name": "Fluorescent Tube Light (40W)", "category": "Lighting", "watts": 40, "hours": 6, "standby_watts": 0, "standby_hours": 0},
    {"name": "Incandescent Yellow Bulb (60W)", "category": "Lighting", "watts": 60, "hours": 5, "standby_watts": 0, "standby_hours": 0},
    {"name": "Desktop Computer (Gaming/Workstation)", "category": "Computing", "watts": 250, "hours": 5, "standby_watts": 5, "standby_hours": 19},
    {"name": "Laptop (Work/Study)", "category": "Computing", "watts": 65, "hours": 6, "standby_watts": 2, "standby_hours": 18},
    {"name": "Smart LED TV 43-55 Inch", "category": "Entertainment", "watts": 85, "hours": 4, "standby_watts": 3, "standby_hours": 20},
    {"name": "Water Geyser / Storage Heater", "category": "Heating", "watts": 2000, "hours": 0.8, "standby_watts": 0, "standby_hours": 0},
    {"name": "Instant Water Heater (3L)", "category": "Heating", "watts": 3000, "hours": 0.3, "standby_watts": 0, "standby_hours": 0},
    {"name": "Microwave Oven", "category": "Kitchen", "watts": 1200, "hours": 0.4, "standby_watts": 2, "standby_hours": 23.6},
    {"name": "Induction Cooktop", "category": "Kitchen", "watts": 1500, "hours": 1.2, "standby_watts": 2, "standby_hours": 22.8},
    {"name": "Fully-Automatic Washing Machine", "category": "Laundry", "watts": 500, "hours": 0.8, "standby_watts": 1, "standby_hours": 23.2},
    {"name": "Electric Iron", "category": "General", "watts": 1000, "hours": 0.5, "standby_watts": 0, "standby_hours": 0},
    {"name": "RO Water Purifier", "category": "Kitchen", "watts": 35, "hours": 3, "standby_watts": 1, "standby_hours": 21},
    {"name": "Wi-Fi Router (24/7 continuous)", "category": "Computing", "watts": 12, "hours": 24, "standby_watts": 0, "standby_hours": 0}
]

def get_current_tariff(session, user_id=1):
    tariff = session.query(Tariff).filter_by(user_id=user_id, is_default=1).first()
    if not tariff:
        tariff = session.query(Tariff).filter_by(is_default=1).first()
    return tariff.to_dict() if tariff else {
        'id': 1, 'name': 'Standard Flat Rate', 'rate_type': 'flat',
        'flat_rate': 7.0, 'fixed_charge': 50.0, 'tax_percent': 5.0, 'slab_json': '[]'
    }

# ----------------- PAGE ROUTES ----------------- #

@app.route('/')
@app.route('/dashboard')
def dashboard():
    session = get_session()
    try:
        tariff = get_current_tariff(session)
        apps = [a.to_dict() for a in session.query(Appliance).filter_by(user_id=1).all()]
        history = [h.to_dict() for h in session.query(BillRecord).filter_by(user_id=1).order_by(BillRecord.id.asc()).limit(12).all()]
        analysis = analyze_appliances(apps, tariff)
        analysis['history'] = history
        analysis['tariff'] = tariff
        return render_template('dashboard.html', active_page='dashboard', initial_data=analysis)
    finally:
        session.close()

@app.route('/appliances')
def appliances_page():
    return render_template('appliances.html', active_page='appliances', presets=APPLIANCE_PRESETS)

@app.route('/bill-calculator')
def bill_calculator_page():
    session = get_session()
    try:
        tariff = get_current_tariff(session)
        return render_template('bill_calculator.html', active_page='bill_calculator', tariff=tariff)
    finally:
        session.close()

@app.route('/savings-simulator')
def savings_simulator_page():
    return render_template('savings_simulator.html', active_page='savings_simulator')

@app.route('/reports')
def reports_page():
    session = get_session()
    try:
        records = [r.to_dict() for r in session.query(BillRecord).filter_by(user_id=1).order_by(BillRecord.id.desc()).all()]
        tariff = get_current_tariff(session)
        return render_template('reports.html', active_page='reports', records=records, tariff=tariff)
    finally:
        session.close()

@app.route('/viva-guide')
def viva_guide_page():
    return render_template('viva_guide.html', active_page='viva_guide')

# ----------------- REST API ROUTES ----------------- #

@app.route('/api/dashboard-data', methods=['GET'])
def api_dashboard_data():
    session = get_session()
    try:
        apps = [a.to_dict() for a in session.query(Appliance).filter_by(user_id=1).all()]
        tariff = get_current_tariff(session)
        history = [h.to_dict() for h in session.query(BillRecord).filter_by(user_id=1).order_by(BillRecord.id.asc()).limit(12).all()]
        
        analysis = analyze_appliances(apps, tariff)
        analysis['tariff'] = tariff
        analysis['history'] = history
        return jsonify(analysis)
    finally:
        session.close()

@app.route('/api/appliances', methods=['GET', 'POST'])
def api_appliances():
    session = get_session()
    try:
        if request.method == 'POST':
            data = request.json or request.form
            name = data.get('name', 'Custom Appliance').strip()
            category = data.get('category', 'General').strip()
            power_watts = float(data.get('power_watts', 100))
            quantity = int(data.get('quantity', 1))
            hours_per_day = float(data.get('hours_per_day', 4))
            days_per_month = int(data.get('days_per_month', 30))
            standby_watts = float(data.get('standby_watts', 0) or 0)
            standby_hours = float(data.get('standby_hours', 0) or 0)

            new_app = Appliance(
                user_id=1,
                name=name,
                category=category,
                power_watts=power_watts,
                quantity=quantity,
                hours_per_day=hours_per_day,
                days_per_month=days_per_month,
                standby_watts=standby_watts,
                standby_hours=standby_hours
            )
            session.add(new_app)
            session.commit()
            return jsonify({'status': 'success', 'id': new_app.id, 'message': f'{name} added successfully!'})

        # GET request
        apps = [a.to_dict() for a in session.query(Appliance).filter_by(user_id=1).order_by(Appliance.id.desc()).all()]
        tariff = get_current_tariff(session)
        analysis = analyze_appliances(apps, tariff)
        return jsonify(analysis)
    finally:
        session.close()

@app.route('/api/appliances/<int:app_id>', methods=['PUT', 'DELETE'])
def api_appliance_modify(app_id):
    session = get_session()
    try:
        app_obj = session.query(Appliance).filter_by(id=app_id, user_id=1).first()
        if not app_obj:
            return jsonify({'error': 'Appliance not found'}), 404

        if request.method == 'DELETE':
            session.delete(app_obj)
            session.commit()
            return jsonify({'status': 'success', 'message': 'Appliance deleted successfully!'})

        if request.method == 'PUT':
            data = request.json
            app_obj.name = data.get('name', app_obj.name)
            app_obj.category = data.get('category', app_obj.category)
            app_obj.power_watts = float(data.get('power_watts', app_obj.power_watts))
            app_obj.quantity = int(data.get('quantity', app_obj.quantity))
            app_obj.hours_per_day = float(data.get('hours_per_day', app_obj.hours_per_day))
            app_obj.days_per_month = int(data.get('days_per_month', app_obj.days_per_month))
            app_obj.standby_watts = float(data.get('standby_watts', 0) or 0)
            app_obj.standby_hours = float(data.get('standby_hours', 0) or 0)

            session.commit()
            return jsonify({'status': 'success', 'message': f'{app_obj.name} updated successfully!'})
    finally:
        session.close()

@app.route('/api/calculate-bill', methods=['POST'])
def api_calculate_bill():
    data = request.json or {}
    units = float(data.get('units', 0))
    rate_type = data.get('rate_type', 'flat')
    flat_rate = float(data.get('flat_rate', 7.0))
    fixed_charge = float(data.get('fixed_charge', 50.0))
    tax_percent = float(data.get('tax_percent', 5.0))
    slabs = data.get('slabs', None)

    tariff = {
        'rate_type': rate_type,
        'flat_rate': flat_rate,
        'fixed_charge': fixed_charge,
        'tax_percent': tax_percent,
        'slab_json': slabs
    }

    result = calculate_bill(units, tariff)
    return jsonify(result)

@app.route('/api/simulate-savings', methods=['POST'])
def api_simulate_savings():
    data = request.json or {}
    session = get_session()
    try:
        tariff = get_current_tariff(session)
        apps = [a.to_dict() for a in session.query(Appliance).filter_by(user_id=1).all()]
    finally:
        session.close()

    app_id = int(data.get('appliance_id', 0))
    target_app = next((a for a in apps if a['id'] == app_id), None)

    if not target_app:
        return jsonify({'error': 'Appliance not found'}), 404

    # Reduction scenario
    hour_reduction = float(data.get('hour_reduction', 1.0))
    new_hours = max(0.0, float(target_app['hours_per_day']) - hour_reduction)
    
    # Upgraded watts scenario
    new_watts = float(data.get('new_watts', target_app['power_watts']))

    # Baseline
    baseline_energy = calculate_appliance_energy(
        target_app['power_watts'], target_app['hours_per_day'],
        target_app['days_per_month'], target_app['quantity']
    )['total_kwh']

    # Simulated
    simulated_energy = calculate_appliance_energy(
        new_watts, new_hours,
        target_app['days_per_month'], target_app['quantity']
    )['total_kwh']

    saved_kwh_month = round(max(0.0, baseline_energy - simulated_energy), 2)
    
    effective_rate = float(tariff.get('flat_rate', 7.0))
    saved_cost_month = round(saved_kwh_month * effective_rate, 2)
    saved_cost_year = round(saved_cost_month * 12, 2)
    co2_saved_month = round(saved_kwh_month * CO2_PER_KWH, 2)
    co2_saved_year = round(co2_saved_month * 12, 2)

    return jsonify({
        'appliance_name': target_app['name'],
        'original_watts': target_app['power_watts'],
        'simulated_watts': new_watts,
        'original_hours': target_app['hours_per_day'],
        'simulated_hours': new_hours,
        'original_kwh': baseline_energy,
        'simulated_kwh': simulated_energy,
        'saved_kwh_month': saved_kwh_month,
        'saved_cost_month': saved_cost_month,
        'saved_cost_year': saved_cost_year,
        'co2_saved_month': co2_saved_month,
        'co2_saved_year': co2_saved_year
    })

@app.route('/api/save-bill-record', methods=['POST'])
def api_save_bill_record():
    data = request.json or request.form
    billing_period = data.get('billing_period', datetime.now().strftime('%b %Y'))
    prev_reading = float(data.get('prev_reading', 0) or 0)
    curr_reading = float(data.get('curr_reading', 0) or 0)
    units_consumed = float(data.get('units_consumed', 0))
    tariff_rate = float(data.get('tariff_rate', 7.0))
    fixed_charge = float(data.get('fixed_charge', 50.0))
    tax_amount = float(data.get('tax_amount', 0))
    estimated_amount = float(data.get('estimated_amount', 0))
    actual_amount = float(data.get('actual_amount', 0) or 0)
    notes = data.get('notes', '')

    session = get_session()
    try:
        new_record = BillRecord(
            user_id=1,
            billing_period=billing_period,
            prev_reading=prev_reading,
            curr_reading=curr_reading,
            units_consumed=units_consumed,
            tariff_rate=tariff_rate,
            fixed_charge=fixed_charge,
            tax_amount=tax_amount,
            estimated_amount=estimated_amount,
            actual_amount=actual_amount,
            notes=notes
        )
        session.add(new_record)
        session.commit()
        return jsonify({'status': 'success', 'id': new_record.id, 'message': f'Record for {billing_period} saved successfully!'})
    finally:
        session.close()

@app.route('/api/bill-record/<int:record_id>', methods=['DELETE'])
def api_delete_bill_record(record_id):
    session = get_session()
    try:
        rec = session.query(BillRecord).filter_by(id=record_id, user_id=1).first()
        if not rec:
            return jsonify({'error': 'Record not found'}), 404
        session.delete(rec)
        session.commit()
        return jsonify({'status': 'success', 'message': 'Bill record deleted.'})
    finally:
        session.close()

@app.route('/api/tariff', methods=['GET', 'POST'])
def api_tariff():
    session = get_session()
    try:
        tariff = session.query(Tariff).filter_by(is_default=1).first()
        if request.method == 'POST':
            data = request.json
            name = data.get('name', 'Custom Tariff')
            rate_type = data.get('rate_type', 'flat')
            flat_rate = float(data.get('flat_rate', 7.0))
            fixed_charge = float(data.get('fixed_charge', 50.0))
            tax_percent = float(data.get('tax_percent', 5.0))
            slab_json = json.dumps(data.get('slabs', [])) if isinstance(data.get('slabs'), list) else data.get('slab_json', '[]')

            if tariff:
                tariff.name = name
                tariff.rate_type = rate_type
                tariff.flat_rate = flat_rate
                tariff.fixed_charge = fixed_charge
                tariff.tax_percent = tax_percent
                tariff.slab_json = slab_json
            else:
                tariff = Tariff(user_id=1, name=name, rate_type=rate_type, flat_rate=flat_rate, fixed_charge=fixed_charge, tax_percent=tax_percent, slab_json=slab_json, is_default=1)
                session.add(tariff)

            session.commit()
            return jsonify({'status': 'success', 'message': 'Tariff configuration updated successfully!'})

        return jsonify(tariff.to_dict() if tariff else {})
    finally:
        session.close()

# ----------------- EXPORT ROUTES (PDF & CSV) ----------------- #

@app.route('/api/export-pdf')
def export_pdf():
    session = get_session()
    try:
        apps = [a.to_dict() for a in session.query(Appliance).filter_by(user_id=1).all()]
        tariff = get_current_tariff(session)
    finally:
        session.close()

    analysis = analyze_appliances(apps, tariff)
    pdf_buffer = generate_pdf_report(analysis, user_name="Student / Household", tariff_name=tariff['name'])

    filename = f"Energy_Audit_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

@app.route('/api/export-csv')
def export_csv():
    session = get_session()
    try:
        apps = [a.to_dict() for a in session.query(Appliance).filter_by(user_id=1).all()]
        tariff = get_current_tariff(session)
    finally:
        session.close()

    analysis = analyze_appliances(apps, tariff)
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write Header Summary
    writer.writerow(["Smart Electricity Bill & Energy Waste Analyzer - Export"])
    writer.writerow(["Export Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(["Total Energy (kWh)", analysis['total_kwh']])
    writer.writerow(["Estimated Monthly Bill (INR)", analysis['bill']['total_amount']])
    writer.writerow(["Carbon Footprint (kg CO2e)", analysis['co2_total_kg']])
    writer.writerow([])
    
    # Appliance Table
    writer.writerow([
        "Rank", "Appliance Name", "Category", "Power (Watts)", "Quantity",
        "Daily Usage Hours", "Days per Month", "Active kWh", "Standby kWh",
        "Total Monthly kWh", "Share (%)", "Estimated Cost (INR)", "CO2 Footprint (kg)"
    ])
    
    for item in analysis['appliances']:
        writer.writerow([
            item['rank'], item['name'], item['category'], item['power_watts'], item['quantity'],
            item['hours_per_day'], item['days_per_month'], item['active_kwh'], item['standby_kwh'],
            item['total_kwh'], item['percentage'], item['estimated_cost'], item['co2_kg']
        ])

    output.seek(0)
    filename = f"Energy_Appliance_Breakdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Smart Electricity Bill & Energy Waste Analyzer on http://127.0.0.1:{port} ...")
    app.run(host='0.0.0.0', port=port, debug=False)
