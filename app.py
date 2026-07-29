"""
CreatorMoneyManager — Amazon Deal Spotter
AI-powered deal finder for content creator equipment.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from config       import (
    OPENROUTER_API_KEY, BOT_TOKEN, CHAT_ID,
    AFFILIATE_ID, MIN_DISCOUNT_PCT, STRONG_DEAL_PCT, MAX_DEALS_SHOWN,
)
from deal_fetcher  import scan_all_deals, CREATOR_PRODUCTS
from deal_analyser import analyse_deal
from deal_alert    import send_deal_alert

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Creator Deal Spotter",
    page_icon="🛒",
    layout="wide",
)

st.title("🛒 Creator Deal Spotter")
st.caption(
    f"Powered by **CreatorMoneyManager** • AI-analysed Amazon deals for content creators • "
    f"{datetime.now().strftime('%A %d %B %Y')}"
)
st.divider()


# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    with st.expander("🔑 API Keys", expanded=not bool(OPENROUTER_API_KEY)):
        st.caption("Keys stored for this session only.")
        ai_key_input    = st.text_input(
            "OpenRouter API Key",
            value=OPENROUTER_API_KEY or "",
            type="password",
            placeholder="Paste your OpenRouter key…"
        )
        bot_token_input = st.text_input(
            "Telegram Bot Token (optional)",
            value=BOT_TOKEN or "",
            type="password"
        )
        chat_id_input   = st.text_input(
            "Telegram Chat ID (optional)",
            value=CHAT_ID or ""
        )

    active_ai_key = ai_key_input.strip()  or OPENROUTER_API_KEY
    active_bot    = bot_token_input.strip() or BOT_TOKEN
    active_chat   = chat_id_input.strip()  or CHAT_ID

    st.divider()
    st.subheader("🎯 Deal Filters")

    min_discount = st.slider(
        "Minimum Discount %",
        min_value=5,
        max_value=60,
        value=int(MIN_DISCOUNT_PCT),
        step=5,
        help="Only show deals with at least this % off the highest recorded price"
    )

    st.markdown("**Categories to scan:**")
    selected_cats = []
    for cat in CREATOR_PRODUCTS.keys():
        if st.checkbox(cat, value=True):
            selected_cats.append(cat)

    st.divider()
    run_ai       = st.toggle("🤖 AI Deal Analysis", value=True,
                             help="AI searches web for reviews and analyses each deal")
    send_telegram = st.toggle("📱 Send to Telegram",  value=False)
    st.divider()
    st.caption(f"🔗 Affiliate ID: `{AFFILIATE_ID}`")
    st.caption("All links support CreatorMoneyManager")


# ── Main tabs ──────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🔍 Deal Scanner", "🏆 Best Deals", "📊 Category Breakdown"])


# ── Tab 1: Scanner ─────────────────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("🔍 AI-Powered Deal Scanner")
        st.write(
            "Scans Amazon creator equipment for genuine discounts — "
            "AI analyses each deal for quality and creator relevance."
        )
    with col2:
        scan_btn = st.button(
            "🚀 Scan for Deals",
            type="primary",
            use_container_width=True,
            disabled=not selected_cats,
        )

    st.divider()

    if scan_btn:
        if not selected_cats:
            st.warning("Please select at least one category to scan.")
        else:
            with st.status("🔍 Scanning Amazon for creator deals...", expanded=True) as status:
                st.write(f"Checking {sum(len(CREATOR_PRODUCTS[c]) for c in selected_cats)} products across {len(selected_cats)} categories...")

                # Fetch deals
                raw_deals = scan_all_deals(
                    affiliate_id=AFFILIATE_ID,
                    min_discount=min_discount,
                    categories=selected_cats,
                )

                if not raw_deals:
                    status.update(label="No deals found above threshold.", state="error")
                    st.warning(f"No deals found with {min_discount}%+ discount. Try lowering the minimum discount filter.")
                    st.stop()

                st.write(f"✅ {len(raw_deals)} deals found above {min_discount}% discount!")

                # AI analysis
                if run_ai and active_ai_key:
                    st.write("🤖 Running AI analysis on each deal...")
                    analysed = []
                    ai_progress = st.progress(0, text="Analysing deals…")
                    for i, deal in enumerate(raw_deals[:MAX_DEALS_SHOWN]):
                        ai_progress.progress(
                            (i + 1) / min(len(raw_deals), MAX_DEALS_SHOWN),
                            text=f"Analysing {deal['name'][:40]}…"
                        )
                        analysed.append(analyse_deal(deal, active_ai_key))
                    ai_progress.empty()
                    deals = analysed
                else:
                    from deal_analyser import _default_analysis
                    deals = [_default_analysis(d) for d in raw_deals[:MAX_DEALS_SHOWN]]

                # Send Telegram
                if send_telegram and active_bot and active_chat:
                    st.write("📱 Sending top deals to Telegram...")
                    top_deals = [d for d in deals if d.get("ai_score", 0) >= 6]
                    if send_deal_alert(active_bot, active_chat, top_deals):
                        st.write(f"✅ {len(top_deals[:5])} deals sent to Telegram!")

                status.update(
                    label=f"✅ Scan complete — {len(deals)} deals analysed",
                    state="complete",
                    expanded=False,
                )

            st.session_state["deals"]     = deals
            st.session_state["last_scan"] = datetime.now().strftime("%H:%M:%S")

    # ── Results ────────────────────────────────────────────────────────────
    if st.session_state.get("deals"):
        deals = st.session_state["deals"]
        st.caption(f"Last scan: {st.session_state.get('last_scan', '—')}")

        # Headline metrics
        m1, m2, m3, m4 = st.columns(4)
        strong_deals  = [d for d in deals if d["discount_pct"] >= STRONG_DEAL_PCT]
        lowest_ever   = [d for d in deals if d.get("is_lowest_ever")]
        buy_now       = [d for d in deals if d.get("ai_buy_rating") == "Buy Now"]

        m1.metric("Deals Found",      len(deals))
        m2.metric("Strong Deals",     len(strong_deals))
        m3.metric("Lowest Ever Price", len(lowest_ever))
        m4.metric("AI: Buy Now",      len(buy_now))
        st.divider()

        # Strong signals
        if strong_deals:
            with st.expander(f"🔥 {len(strong_deals)} Strong Deal(s) — {STRONG_DEAL_PCT:.0f}%+ Off", expanded=True):
                for deal in strong_deals:
                    lowest_tag = " 🔥 **LOWEST EVER PRICE**" if deal.get("is_lowest_ever") else ""
                    st.success(
                        f"{deal['ai_verdict']} **{deal['name']}**{lowest_tag}  \n"
                        f"💰 **${deal['current_price']:.2f}** ({deal['discount_pct']:.0f}% off) | "
                        f"Was: ${deal['highest_price']:.2f} | "
                        f"AI Score: {deal.get('ai_score', '—')}/10 | "
                        f"[🛍️ Buy on Amazon]({deal['affiliate_url']}) | "
                        f"[📊 Price History]({deal['camel_url']})  \n"
                        f"_{deal.get('ai_reason', '')}_"
                    )

        st.divider()

        # Full results table
        st.markdown("#### All Deals")
        df = pd.DataFrame(deals)[[
            "category", "name", "current_price", "highest_price",
            "discount_pct", "ai_verdict", "ai_buy_rating", "ai_score"
        ]].rename(columns={
            "category":      "Category",
            "name":          "Product",
            "current_price": "Price ($)",
            "highest_price": "Was ($)",
            "discount_pct":  "Discount %",
            "ai_verdict":    "AI Verdict",
            "ai_buy_rating": "Rating",
            "ai_score":      "Score",
        })

        def style_score(val):
            if val >= 8:   return "color:#00ff88;font-weight:bold"
            elif val >= 6: return "color:#ffaa00"
            else:          return "color:#ff4444"

        def style_discount(val):
            if val >= STRONG_DEAL_PCT: return "background-color:#1a7a4a;color:white;font-weight:bold"
            elif val >= min_discount:  return "background-color:#4a7a1a;color:white"
            return ""

        st.dataframe(
            df.style
            .map(style_score,    subset=["Score"])
            .map(style_discount, subset=["Discount %"])
            .format({"Price ($)": "${:.2f}", "Was ($)": "${:.2f}", "Discount %": "{:.1f}%"})
            .set_properties(**{"text-align": "center"}),
            use_container_width=True,
        )

        # Affiliate links
        st.divider()
        st.markdown("#### 🛍️ Quick Buy Links")
        st.caption("All links include your CreatorMoneyManager affiliate tag")
        for deal in deals[:10]:
            col_a, col_b, col_c = st.columns([4, 1, 1])
            with col_a:
                st.markdown(f"**{deal['name']}** — {deal['ai_verdict']}")
            with col_b:
                st.markdown(f"[🛍️ Amazon]({deal['affiliate_url']})")
            with col_c:
                st.markdown(f"[📊 History]({deal['camel_url']})")

    else:
        st.info("👆 Press **Scan for Deals** to find the best creator equipment deals on Amazon.")


# ── Tab 2: Best Deals ──────────────────────────────────────────────────────
with tab2:
    st.subheader("🏆 Best Deals — AI Ranked")
    st.write("Top deals ranked by AI score — the ones most worth buying right now.")
    st.divider()

    if st.session_state.get("deals"):
        deals     = st.session_state["deals"]
        top_deals = sorted(deals, key=lambda d: d.get("ai_score", 0), reverse=True)[:10]

        for i, deal in enumerate(top_deals, 1):
            with st.container():
                col_rank, col_info, col_action = st.columns([1, 5, 2])
                with col_rank:
                    score = deal.get("ai_score", 5)
                    color = "#00ff88" if score >= 8 else "#ffaa00" if score >= 6 else "#ff4444"
                    st.markdown(
                        f"<div style='text-align:center;font-size:2rem;color:{color};font-weight:bold'>"
                        f"{score}/10</div>",
                        unsafe_allow_html=True,
                    )
                with col_info:
                    lowest_tag = " 🔥 LOWEST EVER" if deal.get("is_lowest_ever") else ""
                    st.markdown(
                        f"**{i}. {deal['name']}**{lowest_tag}  \n"
                        f"{deal['category']} | {deal['ai_verdict']} | "
                        f"**${deal['current_price']:.2f}** ({deal['discount_pct']:.0f}% off)  \n"
                        f"_{deal.get('ai_reason', '')}_"
                    )
                with col_action:
                    st.markdown(
                        f"**{deal.get('ai_buy_rating', 'Check')}**  \n"
                        f"[🛍️ Buy Now]({deal['affiliate_url']})"
                    )
                st.divider()

        # Send top deals to Telegram
        if st.button("📱 Send Top 5 to Telegram", use_container_width=False):
            if not active_bot or not active_chat:
                st.error("Enter Telegram credentials in the sidebar first.")
            else:
                if send_deal_alert(active_bot, active_chat, top_deals[:5]):
                    st.success("Top 5 deals sent to Telegram! 📱")
                else:
                    st.error("Failed to send. Check your bot token and chat ID.")
    else:
        st.info("Run a scan in the **Deal Scanner** tab first.")


# ── Tab 3: Category Breakdown ──────────────────────────────────────────────
with tab3:
    st.subheader("📊 Category Breakdown")
    st.write("See which product categories have the best deals right now.")
    st.divider()

    if st.session_state.get("deals"):
        deals = st.session_state["deals"]
        df    = pd.DataFrame(deals)

        # Deals per category
        cat_summary = (
            df.groupby("category")
            .agg(
                Deals=("name", "count"),
                Avg_Discount=("discount_pct", "mean"),
                Best_Deal=("discount_pct", "max"),
                Avg_AI_Score=("ai_score", "mean"),
            )
            .round(1)
            .sort_values("Best_Deal", ascending=False)
            .reset_index()
            .rename(columns={"category": "Category", "Avg_Discount": "Avg Discount %", "Best_Deal": "Best Deal %", "Avg_AI_Score": "Avg AI Score"})
        )

        st.dataframe(cat_summary, use_container_width=True)
        st.divider()

        # Bar chart
        st.markdown("#### Best Deal by Category")
        chart_df = cat_summary.set_index("Category")[["Best Deal %"]]
        st.bar_chart(chart_df)

    else:
        st.info("Run a scan in the **Deal Scanner** tab first.")
