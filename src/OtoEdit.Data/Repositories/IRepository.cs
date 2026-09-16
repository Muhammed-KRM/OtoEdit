using System.Linq.Expressions;

namespace OtoEdit.Data.Repositories;

/// <summary>
/// Temel Generic Repository arayüzü.
/// </summary>
/// <typeparam name="T">Entity tipi</typeparam>
public interface IRepository<T> where T : class
{
    Task<T?> GetByIdAsync(Guid id);
    Task<IEnumerable<T>> GetAllAsync(bool asNoTracking = true);
    Task<IEnumerable<T>> FindAsync(Expression<Func<T, bool>> predicate, bool asNoTracking = true);
    IQueryable<T> Query(bool asNoTracking = true);
    Task<T> AddAsync(T entity);
    void Update(T entity);
    void Delete(T entity);
    Task<int> SaveChangesAsync();
}
