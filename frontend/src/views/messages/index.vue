<template>
  <div class="messages-page">
    <div class="page-header">
      <div class="title">消息管理</div>
      <div>
        <el-button @click="handleExport">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </div>
    </div>

    <!-- 搜索表单 -->
    <div class="search-form">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="来源">
          <el-select v-model="searchForm.source" placeholder="全部" clearable>
            <el-option label="企业微信" value="wecom" />
            <el-option label="Telegram" value="telegram" />
            <el-option label="邮件" value="email" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="搜索消息内容" clearable />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 数据表格 -->
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe @row-click="handleRowClick">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="来源" width="100">
          <template #default="{ row }">
            <el-tag :type="getSourceType(row.source)" size="small">
              {{ getSourceName(row.source) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sender_name" label="发送者" width="120" />
        <el-table-column prop="content" label="消息内容" min-width="300" show-overflow-tooltip />
        <el-table-column label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click.stop="handleView(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 消息详情弹窗 -->
    <el-dialog v-model="detailVisible" title="消息详情" width="600px">
      <el-descriptions :column="1" border v-if="currentMessage">
        <el-descriptions-item label="ID">{{ currentMessage.id }}</el-descriptions-item>
        <el-descriptions-item label="来源">
          <el-tag :type="getSourceType(currentMessage.source)" size="small">
            {{ getSourceName(currentMessage.source) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="发送者">{{ currentMessage.sender_name }}</el-descriptions-item>
        <el-descriptions-item label="接收者">{{ currentMessage.receiver_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatTime(currentMessage.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="消息内容">
          <div class="message-content">{{ currentMessage.content }}</div>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import messageApi from '@/api/message'

const loading = ref(false)
const tableData = ref([])
const detailVisible = ref(false)
const currentMessage = ref(null)

const searchForm = reactive({
  source: '',
  keyword: '',
  dateRange: null
})

const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      size: pagination.size,
      source: searchForm.source || undefined,
      keyword: searchForm.keyword || undefined,
      start_date: searchForm.dateRange?.[0],
      end_date: searchForm.dateRange?.[1]
    }
    const res = await messageApi.list(params)
    tableData.value = res.list
    pagination.total = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadData()
}

function handleReset() {
  searchForm.source = ''
  searchForm.keyword = ''
  searchForm.dateRange = null
  handleSearch()
}

function handleView(row) {
  currentMessage.value = row
  detailVisible.value = true
}

function handleRowClick(row) {
  handleView(row)
}

function handleExport() {
  ElMessage.info('导出功能开发中')
}

function getSourceType(source) {
  const types = { wecom: 'success', telegram: 'primary', email: 'warning' }
  return types[source] || 'info'
}

function getSourceName(source) {
  const names = { wecom: '企业微信', telegram: 'Telegram', email: '邮件' }
  return names[source] || source
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}
</script>

<style lang="scss" scoped>
.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.message-content {
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
