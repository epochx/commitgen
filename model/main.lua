include "utils.lua"
require('./encoder')
require('./decoder')
include "predict.lua"

function setup()
	cutorch.manualSeedAll(112300)
	encoder = Encoder({emb_dim=vocab.max_code, emb_out=params.encoder_emb}, params)
	decoder = Decoder({emb_dim=vocab.max_nl, emb_out=params.rnn_size}, params)
end

function fp(state, batch)
	all_h = encoder:forward(batch)
	decoder:forward(state, batch, all_h)
end

function bp(batch)
	local sum_d_all_h = decoder:backward(batch, all_h)
	encoder:backward(batch, sum_d_all_h)
end

function updateParams()
	encoder:updateParameters()
	decoder:updateParameters()
end

function run_val(state) 
	encoder:evaluate()
	decoder:evaluate()
	for _, c_batch in pairs(state.batches) do
		local batch = getInCuda(c_batch)
		fp(state, batch)
	end
	encoder:training()
	decoder:training()
end

-- compute bleu score on test set
function run_bleu(state)
	print('predicting')
	encoder:evaluate()
	decoder:evaluate()
	local predictions, alignments, alphas = unpack(get_predictions(state, params.max_length, params.beam_size, encoder.cell, decoder.cells[1]))
	local tmpFilename = os.tmpname()
	print(tmpFilename)
	local tf = io.open(tmpFilename, 'w')
	for _, line in ipairs(predictions) do
		tf:write(line[1] .. '\t' .. line[2] .. '\n')
	end
	tf:close()
	local cmd
	cmd = 'python ./model/bleu.py ' .. params.dev_ref_file .. ' < ' .. tmpFilename
	print(cmd .. '\n')
	local bleu = tonumber(os.capture(cmd))
	print('BLEU: ' .. bleu .. '\n')

	encoder:training()
	decoder:training()
	return bleu
end

function main()

	local cmd = torch.CmdLine()
	cmd:option('-dataset', '', 'Name of the file/dataset.')
	cmd:option('-gpuidx', 1, 'Index of GPU on which job should be executed.')
	cmd:option('-rnn_size', 400, 'Dimensionality of LSTM')
	cmd:option('-encoder_emb', 400, 'encoder embedding size')
	cmd:option('-decoder_emb', 400, 'decoder embedding size')
	cmd:option('-init_weight', 0.35, 'length')
	cmd:option('-testfile',  'human.data', 'which test file?')
	cmd:option('-dropout', 0.5, 'length')
	cmd:option('-normalize', 1, 'length')
	cmd:option('-beam_size', 10, 'Beam Size')
	cmd:option('-encoder', '', 'output')
	cmd:option('-decoder', '', 'output')
	cmd:option('-lr', 0.5, 'Initial learning rate')
	cmd:option('-shuffle', false, 'Shuffle batches?')
	cmd:option('-language', 'code', 'Code language')

	cmd:text()
	opt = cmd:parse(arg)

	local working_dir = os.getenv("WORK_DIR") .. "/preprocessing"
	local refFileName = working_dir .. '/'.. opt.dataset .. '.' .. opt.language .. '.ref.txt'
	local vocabFileName = working_dir .. '/' .. opt.dataset .. '.' .. opt.language .. '.vocab.data'
	local trainFileName = working_dir .. '/'.. opt.dataset .. '.' .. opt.language .. '.train.data'
	local validFileName = working_dir .. '/'.. opt.dataset .. '.' .. opt.language .. '.valid.data'
	local testFileName = working_dir .. '/'.. opt.dataset .. '.' .. opt.language .. '.test.data'

	params = {
		gpu=opt.gpuidx,
		dev_ref_file=refFileName,
		layers=1,
		rnn_size=opt.rnn_size,
		encoder_emb=opt.encoder_emb,
		decoder_emb=opt.decoder_emb,
		learningRate=opt.lr,
		max_grad_norm=5,
		init_weight=opt.init_weight,
		dropout=opt.dropout,
		decay=0.8,
		normalize=opt.normalize,
		max_length=20,
		beam_size=opt.beam_size,
	}


	vocab = torch.load(vocabFileName)
	print(string.format("Total Tokens: %d", vocab.max_code))
	print(string.format("Total Words: %d", vocab.max_nl))

	state_train = torch.load(trainFileName)
	state_train.name = "training"
	state_val = torch.load(validFileName)
	state_val.name = "validation"
	state_test = torch.load(testFileName)
	local states={state_train, state_val, state_test}

	params.max_nl_length = state_train.max_nl_length
	params.max_code_length = state_train.max_code_length
	params.batch_size = state_train.batch_size

	init_gpu(opt.gpuidx)
	setup()

	local epoch = 0
	if opt.encoder ~= '' and opt.decoder ~= '' then
		print('loading model params')
		encoder_cell_params = torch.load(opt.encoder):getParameters()
		decoder_cell_params = torch.load(opt.decoder):getParameters()
		encoder.paramx:copy(encoder_cell_params)
		decoder.paramx:copy(decoder_cell_params)
	end

	for _, state in pairs(states) do
		reset_state(state)
	end

	local val_accs = {}
	local bleus= {}
	local train_accs = {}
	local start_time = torch.tic()
	local total_cases = 0
	local bleus = {}
	local bestbleu = 0
	print(params)

	local batch_order = {}
	for i = 1, #state_train.batches do
		table.insert(batch_order, i)
	end

	while true do
		total_cases = 0
		start_time = torch.tic()

		if opt.shuffle then
			shuffleTable(batch_order)
		end

		local batch_num = 0
		for _, v in pairs(batch_order) do
			local c_batch = state_train.batches[v]
			local batch = getInCuda(c_batch)

			fp(state_train, batch)
			bp(batch)
			total_cases = total_cases + params.batch_size
			batch_num = batch_num + 1
			updateParams()
		end

		cps = floor(total_cases / torch.toc(start_time))
		epoch = epoch + 1

		local bleu = run_bleu(state_test)
		run_val(state_val)

		-- Reduce learning rate if val acc goes down
		if (#val_accs > 10 and val_accs[#val_accs - 5] >= state_val.acc) then
			params.learningRate = params.learningRate * params.decay
			if params.learningRate < 1e-3 then
				break
			end
		end

		local accs = ""
		for _, state in pairs(states) do
			accs = string.format('%s, %s acc.=%.2f%%',
			accs, state.name, 100.0 * state.acc)
		end

		print('epoch=' .. epoch .. accs ..
		', examples per sec.=' .. cps ..
		', examples=' .. total_cases ..
		', learning rate=' .. string.format("%.3f", params.learningRate) ..
		', gpu=' .. opt.gpuidx)

		if bleu > bestbleu then
			save_models(working_dir)
			bestbleu = bleu
		end

		table.insert(val_accs, state_val.acc)
		table.insert(train_accs, state_train.acc)
		table.insert(bleus, bleu)
		reset_state(state_train)
		reset_state(state_val)
		reset_state(state_test)

		collectgarbage()
	end
end

function save_models(working_dir)
	print('saving models')
	-- save the whole encoder
	torch.save(working_dir .. '/'.. opt.dataset .. '.' .. opt.language .. '.encoder', encoder.cell)

	-- save only the decoder cell
	torch.save(working_dir .. '/'.. opt.dataset .. '.' .. opt.language .. '.decoder', decoder.cells[1])
end

main()
