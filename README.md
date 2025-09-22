# ⚡ ERCOT Nodal LMP Viewer

A simple, interactive appliction for retreviing and visualizing **Location Marginal Prices (LMP)** from the **ERCOT** market on a nodal, bus or hub basis. The app provides a clean GUI for selecting nodes, markets (DAM, RTM, both), and time ranges, then displays the results as interactive graphs with CSV export.
---

## 🚀 Features

- Select **node/bus/hub** for analysis
- Choose **Day-Ahead Market (DAM)**, **Real-Time Market (RTM)**, or both
- Specify **date ranges** for review
- Data formatted in **hourly incremenets**
- Interactive charts
- **Download results** in CSV format

---

## 📂 Project Strucutre
'
ercot-lmp-viewer/
│├── app/        #Strealit App Code
│└── ercot_lmp_app.py
│├── data/       #(optional) cached or sample data
│├── requirements.txt       # Dependencies
│├── READMED.md     # This file
├── gitignore
'
---

## ⚙️ Installation

Clone the repository:
'''bash
git clone https://github.com/patwelch/ercot-lmp-viewer.git
cd ercot-lmp-viewer
'''
Create a virtual environment (recommended):
'''bash
python3 -m venv venv
source venv/bin/activate
venv/Scripts/activate
''' 
Install dependencies:
'''bash
pip install -r requirements.txt
'''

Usage
Run the Streamlit app:
'''bash
streamlit run app/ercot_lmp_app.py
'''
This will open the app in your browser (default: http://localhost:8501)

###📊 Exmaple Workflow
1. Select a node/bus/hub (e.g., HB_HOUSTON)
2. Select DAM, RTM, or Both
3. Choose a **start date** and **end date**
4. Click **Fetch Data**
5. View the interactive chart
6. Download the dataset as a CSV

###🚦 Roadmap
- [ ] Connect to live ERCOT DAM/RTM nodal price feeds
- [ ] Add node autocomplete from ERCOT's node list
- [ ] Overlay DAM vs RTM for comparison
- [ ] Implement cachiong for faster repeat queries
- [ ] Deploy to Streamlit Cloud or container environment

###🤝 Contributing

Contributions are welcome!
- Fork the repo
- create a feature branch (git checkout -b feature/my-feature)
- Commit changes (git commit -m "Add my feature")
- Push to the branch (git push origin feature/my-feature)
- Open a Pull Request

###📜 License

This project is license under the MIT License. See LICENSE for details.

###🖊️ Notes
- This project is for educational and research purposes.
- ERCOT data is publically availabe but subject to ERCOT's terms of use
