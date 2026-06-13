import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from openai import OpenAI

# --- 页面全局设置 ---
st.set_page_config(page_title="直播电商智能 CVP 财务系统", layout="wide")
st.title("📹 直播电商专属 CVP 预测与风控系统")

# --- 侧边栏：AI 引擎配置 ---
with st.sidebar.expander("🧠 AI 诊断引擎配置", expanded=False):
    ai_provider = st.selectbox("选择 AI 大模型", ["DeepSeek (深度求索)", "Kimi (月之暗面)", "智谱 (GLM-4)"])
    api_key = st.text_input("输入对应的 API Key", type="password", placeholder="sk-...")
    
    if ai_provider == "DeepSeek (深度求索)":
        base_url = "https://api.deepseek.com"
        model_name = "deepseek-chat"
    elif ai_provider == "Kimi (月之暗面)":
        base_url = "https://api.moonshot.cn/v1"
        model_name = "moonshot-v1-8k"
    else:
        base_url = "https://open.bigmodel.cn/api/paas/v4/"
        model_name = "glm-4"

st.sidebar.markdown("---")

# --- 侧边栏：1. 行业类目选择 ---
st.sidebar.header("🏷️ 1. 选择服务项目 (类目)")
industry = st.sidebar.radio("不同类目具有不同的成本与退货模型：", ["👗 服饰内衣 (高退货/高毛利)", "💄 美妆护肤 (中退货/高佣金)", "🍔 食品快消 (低退货/低毛利)", "📦 其他自定义类目"])

# 根据行业自动预设参数
if industry == "👗 服饰内衣 (高退货/高毛利)":
    def_price, def_cost, def_rr, def_comm = 150.0, 40.0, 50.0, 15.0
elif industry == "💄 美妆护肤 (中退货/高佣金)":
    def_price, def_cost, def_rr, def_comm = 200.0, 30.0, 15.0, 30.0
elif industry == "🍔 食品快消 (低退货/低毛利)":
    def_price, def_cost, def_rr, def_comm = 50.0, 25.0, 5.0, 10.0
else:
    def_price, def_cost, def_rr, def_comm = 100.0, 30.0, 20.0, 20.0

st.sidebar.markdown("---")

# --- 侧边栏：2. 数据录入模式 ---
st.sidebar.header("📁 2. 核心数据录入")
input_mode = st.sidebar.radio("请选择数据来源：", ["⌨️ 手动精细录入 (单场沙盘)", "📊 Excel 报表导入"])

# 初始化核心参数
data_ready = False

if input_mode == "⌨️ 手动精细录入 (单场沙盘)":
    st.sidebar.markdown("##### 📌 核心收入指标")
    P = st.sidebar.number_input("平均客单价 (元)", min_value=1.0, value=def_price, step=5.0)
    Q = st.sidebar.number_input("单场预计发货单量 (件)", min_value=1.0, value=2000.0, step=100.0)
    R = st.sidebar.slider("预计退货率 (%)", 0.0, 100.0, def_rr, step=1.0) / 100.0
    
    st.sidebar.markdown("##### 💸 抽成比例指标")
    platform_fee = st.sidebar.slider("平台技术服务费扣点 (%)", 0.0, 20.0, 5.0, step=0.5) / 100.0
    host_commission = st.sidebar.slider("主播/达人纯佣金 (%)", 0.0, 60.0, def_comm, step=1.0) / 100.0
    
    st.sidebar.markdown("##### 📦 单件变动成本 (元/件)")
    v_product = st.sidebar.number_input("单件进货/生产成本", min_value=0.0, value=def_cost, step=1.0)
    v_forward_ship = st.sidebar.number_input("单件发货运费+包材", min_value=0.0, value=5.0, step=0.5)
    v_return_ship = st.sidebar.number_input("单件退货运费/退货险", min_value=0.0, value=4.0, step=0.5)
    v_traffic = st.sidebar.number_input("单件投流成本 (CPA)", min_value=0.0, value=15.0, step=1.0)
    
    st.sidebar.markdown("##### 🏢 单场固定成本 (元)")
    F = st.sidebar.number_input("单场固定成本总额 (场地摊销/底薪/样衣等)", min_value=0.0, value=10000.0, step=1000.0)
    
    data_ready = True

elif input_mode == "📊 Excel 报表导入":
    st.sidebar.info("💡 请确保 Excel 包含两列：`参数名称` 和 `数值`。")
    st.sidebar.markdown("*(必填参数名称包括：客单价, 预计发货量, 退货率, 平台扣点, 主播佣金, 进货成本, 发货运费, 退货运费, 单件投流, 固定成本)*")
    uploaded_file = st.sidebar.file_uploader("上传财务报表 (.xlsx)", type=['xlsx', 'xls'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file).set_index('参数名称')
            # 自动映射数据
            P = float(df.loc['客单价', '数值'])
            Q = float(df.loc['预计发货量', '数值'])
            R = float(df.loc['退货率', '数值'])
            if R > 1: R = R / 100.0 
            platform_fee = float(df.loc['平台扣点', '数值'])
            if platform_fee > 1: platform_fee = platform_fee / 100.0
            host_commission = float(df.loc['主播佣金', '数值'])
            if host_commission > 1: host_commission = host_commission / 100.0
            
            v_product = float(df.loc['进货成本', '数值'])
            v_forward_ship = float(df.loc['发货运费', '数值'])
            v_return_ship = float(df.loc['退货运费', '数值'])
            v_traffic = float(df.loc['单件投流', '数值'])
            F = float(df.loc['固定成本', '数值'])
            
            st.sidebar.success("✅ 数据解析成功！")
            data_ready = True
        except Exception as e:
            st.sidebar.error(f"❌ 读取失败，请检查 Excel 格式与参数名称是否对应。错误信息：{e}")

# --- 核心财务逻辑计算 ---
if data_ready:
    # 实际留存率与各项系数
    keep_rate = 1 - R
    percent_fees = platform_fee + host_commission
    
    # 单件边际贡献
    expected_revenue_per_item = P * keep_rate * (1 - percent_fees)
    expected_cost_per_item = v_product + v_forward_ship + v_traffic + (R * v_return_ship)
    
    unit_margin = expected_revenue_per_item - expected_cost_per_item
    
    # 盈亏平衡发货单量
    Q_be = F / unit_margin if unit_margin > 0 else float('inf')
    
    # 预测利润
    profit = Q * unit_margin - F
    msr = (Q - Q_be) / Q if Q_be != float('inf') else -1

    # 风险判定
    if unit_margin <= 0:
        risk_status = "💀 模式破产 (卖一件亏一件)"
    elif msr < 0.1:
        risk_status = "🔴 高风险 (极易亏损)"
    elif msr < 0.2:
        risk_status = "🟡 中等风险 (紧平衡)"
    else:
        risk_status = "🟢 低风险 (利润丰厚)"

    # --- 界面展示区 ---
    tab1, tab2 = st.tabs(["📑 直播单场静态测算 & AI诊断", "🚀 退货率与流量蒙特卡洛模拟"])

    with tab1:
        st.markdown("### 💡 核心测算指标 (单场直播)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📌 单场净利润预测", f"¥ {profit:,.2f}", f"每发一件赚 ¥{unit_margin:.2f}")
        col2.metric("⚖️ 盈亏平衡发货单量", f"{Q_be:.0f} 件" if Q_be != float('inf') else "无法保本")
        col3.metric("📦 实际留存净单量", f"{Q * keep_rate:.0f} 件", f"退货率: {R*100:.1f}%")
        col4.metric("⚠️ 风险评估", risk_status)

        # --- AI 智能诊断模块 ---
        st.markdown("### 🤖 直播复盘本量利分析报告")
        if st.button("✨ 生成财务诊断建议"):
            if not api_key:
                st.error("⚠️ 请先在左侧边栏输入您的 API Key！")
            else:
                with st.spinner(f"正在连接 {ai_provider} 大脑，生成深度诊断中..."):
                    try:
                        client = OpenAI(api_key=api_key, base_url=base_url)
                        prompt = f"""
                        你是一位精通直播电商实操的财务CFO。请根据以下直播单场预测数据，给老板写一份300字大白话商业诊断。
                        要求指出核心亏损或盈利原因，评估投流/佣金/退货率的合理性，并给出极具实操性的打法建议。
                        
                        【直播场次数据】：
                        - 行业类目：{industry}
                        - 客单价：{P}元，预计发货量：{Q}件
                        - 退货率：{R*100}%
                        - 主播+平台总抽成：{percent_fees*100}%
                        - 单件商品综合变动成本（含进货/运费/投流）：{expected_cost_per_item:.2f}元
                        - 单件发货毛利（扣除所有退货/抽成损耗后）：{unit_margin:.2f}元
                        - 单场固定成本：{F}元
                        - 最终预计净利润：{profit:.2f}元
                        - 保本需要发货的单量：{Q_be:.0f}件
                        - 系统风险判定：{risk_status}
                        """
                        response = client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "你是一位直播电商操盘手兼CFO。"},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.7
                        )
                        st.success("✅ 诊断建议生成完毕！")
                        st.info(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"❌ API 请求失败：{e}")

        # 动态图表绘制
        st.markdown("### 📈 发货量盈亏趋势图")
        if unit_margin > 0:
            max_x = int(Q * 1.5) if Q_be < Q * 1.5 else int(Q_be * 1.2)
            x_values = list(range(0, max_x + 50, max_x // 50 if max_x > 50 else 1))
            
            revenue_values = [x * expected_revenue_per_item for x in x_values]
            total_cost_values = [F + x * expected_cost_per_item for x in x_values]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=x_values, y=revenue_values, mode='lines', name='扣除抽成后净收入', line=dict(color='#1f77b4', width=3)))
            fig.add_trace(go.Scatter(x=x_values, y=total_cost_values, mode='lines', name='综合总成本', line=dict(color='#d62728', width=3)))
            fig.add_hline(y=F, line_dash="dash", line_color="orange", annotation_text=f"固定成本 ({F:,.0f})")
            
            if Q_be <= max_x:
                fig.add_trace(go.Scatter(x=[Q_be], y=[F + Q_be * expected_cost_per_item], mode='markers', name='盈亏平衡发货量', marker=dict(color='black', size=10, symbol='x')))
            fig.add_trace(go.Scatter(x=[Q], y=[revenue_values[x_values.index(min(x_values, key=lambda x:abs(x-Q)))]], mode='markers', name='目标发货点', marker=dict(color='green', size=12, symbol='star')))

            fig.update_layout(xaxis_title="发货单量 (件)", yaxis_title="金额 (元)", hovermode="x unified", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("📉 警告：您的单件边际贡献为负数！这意味着卖得越多亏得越多，图表无法呈现盈利趋势。请立即调整售价、降低退货率或削减投流成本！")

    with tab2:
        st.markdown("### 🎲 极端退货率与流量波动模拟 (运行 10,000 次)")
        st.write("直播中最不可控的是**退货率**和**自然流转化波动**。本模块将模拟这两者随机波动时，您的单场盈利胜率。")
        
        col_a, col_b = st.columns(2)
        with col_a:
            q_std = st.slider("发货量波动幅度 (±%)", 10, 80, 30) / 100.0
        with col_b:
            r_std = st.slider("退货率绝对波动评估 (±%)", 2, 20, 5) / 100.0
            
        if st.button("🚀 启动万场直播平行推演"):
            if unit_margin <= 0 and profit < 0:
                 st.error("当前业务模式必定亏损，无需进行概率模拟，请先调整基础参数！")
            else:
                with st.spinner("正在推演 10,000 场直播..."):
                    simulations = 10000
                    random_Q = np.random.normal(Q, Q * q_std / 3, simulations)
                    random_Q = np.where(random_Q < 0, 0, random_Q) 
                    
                    random_R = np.random.normal(R, r_std / 3, simulations)
                    random_R = np.clip(random_R, 0, 0.99) 
                    
                    sim_revenue_per_item = P * (1 - random_R) * (1 - percent_fees)
                    sim_cost_per_item = v_product + v_forward_ship + v_traffic + (random_R * v_return_ship)
                    profits = random_Q * (sim_revenue_per_item - sim_cost_per_item) - F
                    
                    win_rate = (profits > 0).sum() / simulations * 100
                    avg_profit = np.mean(profits)
                    worst_case = np.percentile(profits, 5)
                    
                    st.markdown("#### 📊 模拟诊断报告")
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("单场盈利胜率", f"{win_rate:.1f} %", "目标应 > 75%")
                    sc2.metric("平均预期净利润", f"¥ {avg_profit:,.0f}")
                    sc3.metric("翻车悲观预期 (5%极差情况)", f"¥ {worst_case:,.0f}")
                    
                    fig_hist = go.Figure(data=[go.Histogram(x=profits, nbinsx=100, marker_color='#8c564b')])
                    fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="生死线")
                    fig_hist.add_vline(x=avg_profit, line_dash="solid", line_color="green", annotation_text="平均利润")
                    fig_hist.update_layout(title_text='10,000 场平行宇宙直播利润分布', xaxis_title='利润金额 (元)', yaxis_title='出现次数')
                    st.plotly_chart(fig_hist, use_container_width=True)