using System.Data;
using Dapper;

namespace Infrastructure.Repositories;

public class BoolIntHandler : SqlMapper.TypeHandler<bool>
{
    public override bool Parse(object value) => Convert.ToInt32(value) == 1;

    public override void SetValue(IDbDataParameter parameter, bool value)
    {
        parameter.Value = value ? 1 : 0;
    }
}
