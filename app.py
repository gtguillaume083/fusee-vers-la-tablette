# --- Graphique de progression dans le temps ---
if history:
    df = pd.DataFrame(history)
    df["delta"] = df["delta"].astype(int)

    # 🔧 Corriger le parsing des dates sans année
    def parse_school_date(date_str):
        try:
            d = datetime.datetime.strptime(date_str, "%d/%m %H:%M")
            today = datetime.datetime.now()
            school_year = today.year if d.month >= 9 else today.year - 1
            return d.replace(year=school_year)
        except Exception:
            return pd.NaT

    df["time"] = df["time"].apply(parse_school_date)
    df = df.dropna(subset=["time"])
    df = df.sort_values("time")

    # 🧮 Calcul de la progression cumulée dans le temps
    altitude = []
    total = 0
    for _, row in df.iterrows():
        total += row["delta"] if row["action"] == "up" else -row["delta"]
        altitude.append(max(0, total))
    df["altitude"] = altitude

    # 📆 Définir la période de l'année scolaire
    today = datetime.datetime.now()
    start_date = datetime.datetime(today.year if today.month >= 9 else today.year - 1, 9, 1)
    end_date = datetime.datetime(start_date.year + 1, 6, 30)

    # Créer la série complète pour interpolation
    df_full = pd.DataFrame({"date": pd.date_range(start=start_date, end=end_date, freq="D")})
    df_full = pd.merge_asof(
        df_full.sort_values("date"),
        df.sort_values("time").rename(columns={"time": "date"}),
        on="date",
        direction="forward"
    )

    df_full["altitude"].fillna(method="ffill", inplace=True)
    df_full["altitude"].fillna(0, inplace=True)

    # 🎯 Ne garder que jusqu'à aujourd'hui
    df_interp = df_full[df_full["date"] <= today]
    fus_alt = df_interp["altitude"].iloc[-1]

    # 📈 Création du graphique
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_interp["date"],
        y=df_interp["altitude"],
        mode="lines",
        line=dict(color="skyblue", width=4),
        name="Progression"
    ))

    # 🌌 Ligne de Karman (100 %)
    fig.add_hline(
        y=100,
        line=dict(color="red", dash="dot"),
        name="Ligne de Karman"
    )
    fig.add_annotation(
        xref="paper",
        x=1.02,
        y=105,  # 👉 Position au-dessus de la ligne
        text="🌌 Ligne de Karman (100%)",
        showarrow=False,
        font=dict(size=12, color="red")
    )

    # 🚀 Position de la fusée
    fig.add_trace(go.Scatter(
        x=[df_interp["date"].iloc[-1]],
        y=[fus_alt],
        mode="markers+text",
        marker=dict(size=30, symbol="star", color="orange"),
        text=["🚀"],
        textposition="top center",
        name="Fusée"
    ))

    # ✨ Mise en page
    fig.update_layout(
        title="Trajectoire de la fusée",
        xaxis_title="Temps (du 1er septembre au 30 juin)",
        yaxis_title="Altitude (%)",
        yaxis=dict(range=[0, max(130, fus_alt + 10)]),  # 👉 Autorise jusqu’à 130 %
        width=900,
        height=500,
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Texte sous le graphique ---
    st.markdown("### 🧭 Altitude actuelle :")
    st.metric(label="Progression", value=f"{progress} %")

    st.markdown("## 📜 Historique des actions")
    for h in history:
        st.markdown(
            f"🕓 **{h['time']}** — *{h['action']} de {h['delta']} %* : {h['reason']}"
        )

else:
    st.info("Aucune trajectoire à afficher 🚀")
