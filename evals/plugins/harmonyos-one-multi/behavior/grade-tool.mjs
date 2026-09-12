// A normal OpenCode tool enforces complete grading data without relying on
// OutputFormatJsonSchema, whose 1.18.29 message endpoint rejects this payload.
export function gradeToolSource(count,sdkUrl){
 return `import {tool} from ${JSON.stringify(sdkUrl)};
 const evidence=tool.schema.array(tool.schema.string().min(1)).min(1);
 const criterion=tool.schema.object({index:tool.schema.number().int().min(0).max(${count-1}),pass:tool.schema.boolean(),evidence,explanation:tool.schema.string().min(1)});
 const error=tool.schema.object({type:tool.schema.string().min(1),evidence,explanation:tool.schema.string().min(1)});
 const side=tool.schema.object({criteria:tool.schema.array(criterion).length(${count}),redundantQuestions:tool.schema.number().int().min(0),boundaryQuestion:tool.schema.boolean(),criticalErrors:tool.schema.array(error)});
 export default async()=>({tool:{submit_grade:tool({description:'Submit independent anonymous A/B grades. Each side must cover all ${count} criteria in index order, with actual trace or artifact citations. Submit exactly once.',args:{A:side,B:side,comparison:tool.schema.string()},async execute(args){for(const side of [args.A,args.B]){if(side.criteria.some((item,index)=>item.index!==index))throw new Error('Every criterion must occur once in index order.');}return JSON.stringify({accepted:true});}})}});`;
}
