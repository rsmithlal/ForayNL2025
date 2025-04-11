from flask import Flask, render_template, request, send_file
import pandas as pd
import io

app = Flask(__name__, template_folder='templates')

# Load data
RESULT_PATH = 'data/matching_result_apr_2025.csv'  # same name
FORAY_PATH = 'data/2023ForayNL_Fungi.csv'
MYCOBANK_PATH = 'data/MBList.csv'

result_df = pd.read_csv(RESULT_PATH)
foray_df = pd.read_csv(FORAY_PATH, encoding='latin-1')
myco_df = pd.read_csv(MYCOBANK_PATH, encoding='latin-1')

result_df['Similarity'] = result_df['Similarity'].round(0).astype(int)

# Home route
@app.route('/', methods=['GET', 'POST'])
def index():
    global filtered_df
    filtered_df = result_df.copy()

    search = request.form.get('search', '').strip()
    status_filter = request.form.get('status_filter')
    sim_filters = request.form.getlist('sim_filter')
    explanation_filter = request.form.get('explanation_filter')
    question_mark_filter = request.form.get('question_mark_filter')

    if search:
        filtered_df = filtered_df[filtered_df['Foray_Name'].str.contains(search, case=False, na=False)]

    if status_filter and status_filter != 'All':
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]

    if sim_filters:
        sim_condition = pd.Series([False] * len(filtered_df))
        for sf in sim_filters:
            if sf == '100':
                sim_condition |= (filtered_df['Similarity'] == 100)
            elif sf == '90-100':
                sim_condition |= (filtered_df['Similarity'] >= 90) & (filtered_df['Similarity'] < 100)
            elif sf == '80-90':
                sim_condition |= (filtered_df['Similarity'] >= 80) & (filtered_df['Similarity'] < 90)
            elif sf == '70-80':
                sim_condition |= (filtered_df['Similarity'] >= 70) & (filtered_df['Similarity'] < 80)
            elif sf == '50-70':
                sim_condition |= (filtered_df['Similarity'] >= 50) & (filtered_df['Similarity'] < 70)
            elif sf == '<50':
                sim_condition |= (filtered_df['Similarity'] < 50) & (filtered_df['Status'] != 'NO_MATCH')
            elif sf == 'NO MATCH':
                sim_condition |= (filtered_df['Status'] == 'NO_MATCH')
        filtered_df = filtered_df[sim_condition]

    if explanation_filter and explanation_filter != 'All':
        filtered_df = filtered_df[filtered_df['Explanation'] == explanation_filter]

    if question_mark_filter == 'Contains':
        filtered_df = filtered_df[
            filtered_df['Foray_Name'].astype(str).str.contains(r'\?', na=False)
        ]
    elif question_mark_filter == 'Not Contains':
        filtered_df = filtered_df[
            ~filtered_df['Foray_Name'].astype(str).str.contains(r'\?', na=False)
        ]

    return render_template('index.html', tables=filtered_df.to_dict(orient='records'), search=search, total=len(filtered_df))

# Detail route
@app.route('/detail/<foray_id>')
def detail(foray_id):
    result_row = result_df[result_df['Foray_ID'] == foray_id].iloc[0]
    foray_row = foray_df[foray_df['id'] == foray_id].to_dict(orient='records')
    myco_row = myco_df[myco_df['MycoBank #'] == result_row['MycoBank_ID']].to_dict(orient='records')
    return render_template('detail.html', result=dict(result_row), foray=foray_row, myco=myco_row)

# CSV download route (filtered)
@app.route('/download', methods=['GET', 'POST'])
def download():
    global filtered_df
    buffer = io.StringIO()
    filtered_df.to_csv(buffer, index=False)
    buffer.seek(0)
    return send_file(io.BytesIO(buffer.getvalue().encode()),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='filtered_result.csv')

if __name__ == '__main__':
    app.run(debug=True)
