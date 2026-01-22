<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #409EFF;">
            <el-icon size="24"><ChatDotRound /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.todayMessages }}</div>
            <div class="stat-label">今日消息</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #67C23A;">
            <el-icon size="24"><Calendar /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.todayBirthdays }}</div>
            <div class="stat-label">今日生日</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #E6A23C;">
            <el-icon size="24"><Message /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalMessages }}</div>
            <div class="stat-label">总消息数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #909399;">
            <el-icon size="24"><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalContacts }}</div>
            <div class="stat-label">联系人</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover">
          <template #header>
            <span>今日待办提醒</span>
          </template>
          <div class="todo-list">
            <div v-if="todos.length === 0" class="empty">暂无待办</div>
            <div v-for="(todo, index) in todos" :key="index" class="todo-item">
              <el-checkbox :model-value="false" disabled />
              <span class="todo-text">{{ todo.text }}</span>
              <el-tag size="small">{{ todo.doc_name }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover">
          <template #header>
            <span>今日生日</span>
          </template>
          <div class="birthday-list">
            <div v-if="birthdays.length === 0" class="empty">今日无人生日</div>
            <div v-for="(person, index) in birthdays" :key="index" class="birthday-item">
              <el-avatar :size="36">{{ person.name[0] }}</el-avatar>
              <div class="birthday-info">
                <div class="name">{{ person.name }}</div>
                <div class="age">{{ person.age }}岁</div>
              </div>
              <el-tag type="success" size="small">生日快乐</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const stats = ref({
  todayMessages: 0,
  todayBirthdays: 0,
  totalMessages: 0,
  totalContacts: 0
})

const todos = ref([])
const birthdays = ref([])

onMounted(async () => {
  try {
    // 获取统计数据
    stats.value = await request.get('/dashboard/stats')
    // 获取今日待办
    todos.value = await request.get('/dashboard/todos')
    // 获取今日生日
    birthdays.value = await request.get('/dashboard/birthdays')
  } catch (e) {
    console.error('获取数据失败', e)
  }
})
</script>

<style lang="scss" scoped>
.stat-card {
  display: flex;
  align-items: center;
  padding: 10px;

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    margin-right: 12px;

    @media screen and (max-width: 768px) {
      width: 40px;
      height: 40px;
    }
  }

  .stat-value {
    font-size: 24px;
    font-weight: bold;
    color: #303133;

    @media screen and (max-width: 768px) {
      font-size: 20px;
    }
  }

  .stat-label {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;

    @media screen and (max-width: 768px) {
      font-size: 12px;
    }
  }

  @media screen and (max-width: 768px) {
    padding: 8px;
  }
}

.todo-list, .birthday-list {
  .empty {
    text-align: center;
    color: #909399;
    padding: 20px 0;

    @media screen and (max-width: 768px) {
      padding: 16px 0;
    }
  }
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f2f5;

  &:last-child {
    border-bottom: none;
  }

  .todo-text {
    flex: 1;
  }

  @media screen and (max-width: 768px) {
    padding: 10px 0;
    gap: 8px;

    .todo-text {
      font-size: 14px;
    }
  }
}

.birthday-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f2f5;

  &:last-child {
    border-bottom: none;
  }

  .birthday-info {
    flex: 1;

    .name {
      font-weight: 500;
    }

    .age {
      font-size: 12px;
      color: #909399;
    }
  }

  @media screen and (max-width: 768px) {
    padding: 10px 0;
    gap: 8px;

    .name {
      font-size: 14px;
    }
  }
}
</style>
