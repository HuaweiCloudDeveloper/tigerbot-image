
import streamlit as st
import os
import torch
from datetime import datetime

# 自定义模块（确保该模块路径正确）
from utils.modeling_hack import get_model

# 设置页面标题
st.set_page_config(page_title="TigerBot - 基础问答", layout="wide")
st.title(" TigerBot - 基础问答 (CPU Mode)")

# 模型根目录
MODEL_PATH = "/home/TigerBot/model"

# 获取所有子文件夹作为模型选项
try:
    models = [name for name in os.listdir(MODEL_PATH) if os.path.isdir(os.path.join(MODEL_PATH, name))]
except FileNotFoundError:
    st.error(f"Model path '{MODEL_PATH}' not found.")
    st.stop()

# 用户选择模型
selected_model = st.selectbox("Choose a model", models)

# 如果选择了模型，则加载模型
if selected_model:
    model_dir = os.path.join(MODEL_PATH, selected_model)

    @st.cache_resource
    def load_model(model_path):
        print(f'Loading model from: {model_path}')
        return get_model(model_path=model_path)

    try:
        model, tokenizer, generation_config = load_model(model_dir)
        model.to('cpu')  # 确保在 CPU 上运行
    except Exception as e:
        st.error(f"Failed to load model: {e}")
        st.stop()

    # 初始化会话状态
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history_sessions" not in st.session_state:
        st.session_state.history_sessions = []

    # 侧边栏：新建对话 & 历史记录
    with st.sidebar:
        st.header("对话管理")

        if st.button("新建对话"):
            st.session_state.messages = []

        st.subheader("历史对话")
        for idx, session in enumerate(st.session_state.history_sessions):
            timestamp = session["timestamp"]
            title = f"{idx + 1}. {timestamp}"
            if st.button(title, key=f"session_{idx}"):
                st.session_state.messages = session["messages"]

    # 显示聊天记录（兼容旧版 Streamlit）
    chat_container = st.container()
    with chat_container:
        content_html = ""
        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"].replace("\n", "<br>")
            color = "blue" if role == "user" else "green"
            content_html += f'<div style="margin:10px;padding:10px;border-left:3px solid {color};"><b>{role}:</b> {content}</div>'
        st.markdown(f"""
        <div style="max-height:500px;overflow-y:auto;border:1px solid #ccc;padding:10px;margin-bottom:10px;">
            {content_html}
        </div>
        """, unsafe_allow_html=True)

    # 输入区域
    user_input = st.text_area("请输入您的问题...", key="main_input")
    send_button = st.button("发送")

    # 处理用户输入
    if send_button and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 构造输入并推理
        inputs = tokenizer(user_input, return_tensors='pt', truncation=True, max_length=512).to('cpu')
        outputs = model.generate(
            input_ids=inputs['input_ids'],
            attention_mask=inputs['attention_mask'],
            generation_config=generation_config
        )
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

        # 清空输入框并刷新
        st.experimental_rerun()

    # 保存当前对话为历史记录
    if send_button and user_input:
        current_session = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": st.session_state.messages.copy()
        }
        st.session_state.history_sessions.append(current_session)
