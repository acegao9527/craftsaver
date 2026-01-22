<template>
  <div class="birthday-page">
    <div class="page-header">
      <div class="title">生日管理</div>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        添加生日
      </el-button>
    </div>

    <!-- 搜索表单 -->
    <div class="search-form">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="请输入姓名" clearable />
        </el-form-item>
        <el-form-item label="月份">
          <el-select v-model="searchForm.month" placeholder="全部" clearable>
            <el-option v-for="m in 12" :key="m" :label="`${m}月`" :value="m" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 数据表格 -->
    <el-card shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column label="生日" width="150">
          <template #default="{ row }">
            {{ row.birth_date }}
          </template>
        </el-table-column>
        <el-table-column prop="calendar_type" label="历法" width="100">
          <template #default="{ row }">
            <el-tag :type="row.calendar_type === 'lunar' ? 'warning' : 'success'">
              {{ row.calendar_type === 'lunar' ? '农历' : '公历' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
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

    <!-- 添加/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="历法" prop="calendar_type">
          <el-radio-group v-model="form.calendar_type">
            <el-radio label="solar">公历</el-radio>
            <el-radio label="lunar">农历</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="生日" prop="date">
          <el-date-picker
            v-model="form.date"
            type="monthday"
            format="MM月dd日"
            value-format="MM-dd"
            placeholder="选择月日"
          />
        </el-form-item>
        <el-form-item label="年份">
          <el-input v-model="form.year" type="number" placeholder="出生年份（选填，默认1900）" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="3" placeholder="备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import birthdayApi from '@/api/birthday'

const loading = ref(false)
const saving = ref(false)
const tableData = ref([])
const dialogVisible = ref(false)
const dialogTitle = ref('添加生日')
const formRef = ref(null)

const searchForm = reactive({
  name: ''
})

const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

const form = reactive({
  id: null,
  name: '',
  date: '',
  year: '',
  calendar_type: 'solar',
  note: ''
})

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  date: [{ required: true, message: '请选择生日', trigger: 'change' }]
}

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const res = await birthdayApi.list({
      page: pagination.page,
      size: pagination.size,
      ...searchForm
    })
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
  searchForm.name = ''
  handleSearch()
}

function handleAdd() {
  form.id = null
  form.name = ''
  form.date = ''
  form.year = ''
  form.calendar_type = 'solar'
  form.note = ''
  dialogTitle.value = '添加生日'
  dialogVisible.value = true
}

function handleEdit(row) {
  form.id = row.id
  form.name = row.name
  // Parse birth_date (YYYY-MM-DD) to date and year
  const [y, m, d] = row.birth_date.split('-')
  form.date = `${m}-${d}`
  form.year = y === '1900' ? '' : y
  form.calendar_type = row.calendar_type || 'solar'
  form.note = row.note || ''
  dialogTitle.value = '编辑生日'
  dialogVisible.value = true
}

async function handleSave() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      const year = form.year ? form.year : '1900'
      const birth_date = `${year}-${form.date}`
      
      const data = {
        name: form.name,
        birth_date: birth_date,
        calendar_type: form.calendar_type,
        note: form.note
      }

      if (form.id) {
        await birthdayApi.update(form.id, data)
        ElMessage.success('更新成功')
      } else {
        await birthdayApi.add(data)
        ElMessage.success('添加成功')
      }

      dialogVisible.value = false
      loadData()
    } catch (e) {
      console.error(e)
    } finally {
      saving.value = false
    }
  })
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除 "${row.name}" 的生日记录吗？`, '确认删除', {
      type: 'warning'
    })
    await birthdayApi.delete(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
    }
  }
}
</script>

<style lang="scss" scoped>
.tip {
  margin-left: 8px;
  color: #909399;
}
.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
