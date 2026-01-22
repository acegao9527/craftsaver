<template>
  <div class="lottery-container">
    <div class="content">
      <div class="header">
        <h1>🎉 幸运大抽奖</h1>
        <p>输入您的名字，等待命运的召唤！</p>
      </div>

      <div class="form-box">
        <el-input 
          v-model="name" 
          placeholder="请输入您的姓名" 
          class="name-input"
          size="large"
          :prefix-icon="User"
          @keyup.enter="handleJoin"
        />
        
        <el-button 
          type="primary" 
          class="submit-btn" 
          size="large" 
          @click="handleJoin" 
          :loading="loading"
          round
        >
          立即报名
        </el-button>
      </div>

      <div v-if="success" class="result-box">
        <el-result
          icon="success"
          title="报名成功"
          sub-title="请留意群内抽奖通知"
        >
        </el-result>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { User } from '@element-plus/icons-vue'
import { joinLottery } from '@/api/lottery'
import { ElMessage } from 'element-plus'

const name = ref('')
const loading = ref(false)
const success = ref(false)

const handleJoin = async () => {
  if (!name.value.trim()) {
    ElMessage.warning('请输入姓名')
    return
  }

  loading.value = true
  try {
    await joinLottery({ name: name.value })
    success.value = true
    name.value = '' // clear input
    ElMessage.success('报名成功！')
  } catch (error) {
    console.error(error)
    ElMessage.error('报名失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.lottery-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.content {
  background: rgba(255, 255, 255, 0.95);
  padding: 40px 30px;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.header {
  margin-bottom: 30px;
  
  h1 {
    font-size: 28px;
    color: #333;
    margin-bottom: 10px;
  }
  
  p {
    color: #666;
    font-size: 14px;
  }
}

.form-box {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.name-input {
  font-size: 16px;
}

.submit-btn {
  width: 100%;
  font-weight: bold;
  font-size: 18px;
  height: 50px;
}

.result-box {
  margin-top: 20px;
  animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
