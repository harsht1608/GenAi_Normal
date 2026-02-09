import streamlit as st
import requests

# FastAPI backend URL
FASTAPI_URL = "http://localhost:8000"  # Update if running elsewhere

st.set_page_config(page_title="AI-Powered DevOps Assistant", page_icon="🤖", layout="centered")
st.title("🤖 AI-Powered DevOps Assistant")

# Main tabs for different features
tab1, tab2 = st.tabs(["💬 Chatbot", "🛠️ DevOps Helpers"])

# --- TAB 1: Chatbot ---
with tab1:
    st.subheader("Chat with AI Assistant")
    user_prompt = st.text_area("Enter your prompt:", placeholder="Ask me anything...", height=120)
    
    if st.button("Ask AI", key="chat"):
        if user_prompt.strip():
            try:
                response = requests.post(
                    f"{FASTAPI_URL}/ask-gemini",
                    json={"prompt": user_prompt}
                )
                response.raise_for_status()
                ai_response = response.json().get("response", "")
                if ai_response:
                    st.success("Response:")
                    st.write(ai_response)
                else:
                    st.warning("No response received.")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error: {e}")
        else:
            st.warning("⚠️ Please enter a prompt.")

# --- TAB 2: DevOps Helpers ---
with tab2:
    st.subheader("🛠️ DevOps Helpers")
    
    # Nested tabs for DevOps tools
    devops_tab1, devops_tab2, devops_tab3 = st.tabs([
        "📊 Analyze Tools",
        "🏗️ Generate Code",
        "🔐 Security Scanning"
    ])
    
    # --- ANALYZE TOOLS ---
    with devops_tab1:
        st.subheader("📊 Analysis Tools")
        
        analysis_tool = st.selectbox(
            "Choose analysis tool:",
            ["📋 Analyze Logs", "🐳 Optimize Dockerfile", "🔄 Fix CI/CD Pipeline"],
            key="analyze_select"
        )
        
        content = st.text_area(
            "Paste content to analyze:",
            placeholder="Paste logs, Dockerfile, or CI/CD YAML...",
            height=250,
            key="analyze_content"
        )
        
        if st.button("🔍 Analyze", key="analyze"):
            if content.strip():
                try:
                    endpoint_map = {
                        "📋 Analyze Logs": "analyze-logs",
                        "🐳 Optimize Dockerfile": "optimize-docker",
                        "🔄 Fix CI/CD Pipeline": "fix-ci"
                    }
                    endpoint = endpoint_map[analysis_tool]
                    
                    with st.spinner("Analyzing..."):
                        response = requests.post(
                            f"{FASTAPI_URL}/{endpoint}",
                            json={"content": content}
                        )
                    response.raise_for_status()
                    suggestions = response.json().get("suggestions", "")
                    if suggestions:
                        st.success(f"✅ Analysis Results:")
                        st.write(suggestions)
                    else:
                        st.warning("No analysis returned.")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Error: {e}")
            else:
                st.warning("⚠️ Please paste content first.")
    
    # --- GENERATE CODE ---
    with devops_tab2:
        st.subheader("🏗️ Code Generation")
        
        generation_type = st.selectbox(
            "What would you like to generate?",
            [
                "🐳 Dockerfile",
                "⚙️ CI/CD Pipeline",
                "☸️ Kubernetes Manifests",
                "🌍 Infrastructure as Code"
            ],
            key="gen_select"
        )
        
        description = st.text_area(
            "Describe what you need:",
            placeholder="E.g., 'Create a Dockerfile for a Python FastAPI app with PostgreSQL'",
            height=200,
            key="gen_desc"
        )
        
        if st.button("✨ Generate", key="generate"):
            if description.strip():
                try:
                    endpoint_map = {
                        "🐳 Dockerfile": "generate-dockerfile",
                        "⚙️ CI/CD Pipeline": "generate-cicd",
                        "☸️ Kubernetes Manifests": "generate-k8s",
                        "🌍 Infrastructure as Code": "generate-iac"
                    }
                    endpoint = endpoint_map[generation_type]
                    
                    with st.spinner("Generating..."):
                        response = requests.post(
                            f"{FASTAPI_URL}/{endpoint}",
                            json={"description": description}
                        )
                    response.raise_for_status()
                    generated_code = response.json().get("code", "")
                    if generated_code:
                        st.success("✅ Generated Code:")
                        st.code(generated_code, language="yaml")
                        
                        st.download_button(
                            label="📋 Download Generated Code",
                            data=generated_code,
                            file_name=f"generated_{endpoint}.txt",
                            mime="text/plain"
                        )
                    else:
                        st.warning("No code generated.")
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Error: {e}")
            else:
                st.warning("⚠️ Please describe what you need.")
    
    # --- SECURITY SCANNING ---
    with devops_tab3:
        st.subheader("🔐 Security & Vulnerability Scanning")
        
        security_tool = st.selectbox(
            "Security Tool:",
            ["🛡️ Scan Dependencies (requirements.txt)"],
            key="sec_select"
        )
        
        requirements = st.text_area(
            "Paste your requirements.txt file:",
            placeholder="fastapi==0.115.6\nrequests==2.32.3\n...",
            height=250,
            key="sec_content"
        )
        
        if st.button("🛡️ Scan Security", key="security"):
            if requirements.strip():
                try:
                    with st.spinner("Scanning for vulnerabilities..."):
                        response = requests.post(
                            f"{FASTAPI_URL}/scan-security",
                            json={"requirements": requirements}
                        )
                    response.raise_for_status()
                    result = response.json()
                    
                    vuln = result.get("vulnerabilities", "")
                    recommend = result.get("recommendations", "")
                    
                    st.subheader("🔍 Vulnerability Scan Results")
                    if "No vulnerabilities" in vuln:
                        st.success("✅ No vulnerabilities detected!")
                    else:
                        st.warning("⚠️ Vulnerabilities found:")
                        st.code(vuln, language="json")
                    
                    st.subheader("💡 Recommendations")
                    st.write(recommend)
                    
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Error: {e}")
            else:
                st.warning("⚠️ Please paste your requirements.txt.")

# --- Footer ---
st.markdown(
    """
    <div style="
        position: fixed; 
        bottom: 15px; 
        left: 50%; 
        transform: translateX(-50%);
        color: grey; 
        font-size: 13px;
        text-align: center;
    ">
        🚀 AI-Powered DevOps Assistant | Made with ❤️ by Harsh
    </div>
    """,
    unsafe_allow_html=True
)

# --- Footer ---
st.markdown(
    """
    <div style="
        position: fixed; 
        bottom: 15px; 
        left: 50%; 
        transform: translateX(-50%);
        color: grey; 
        font-size: 13px;
        text-align: center;
    ">
        🚀 AI-Powered DevOps Assistant | Made with ❤️ by Harsh
    </div>
    """,
    unsafe_allow_html=True
)
